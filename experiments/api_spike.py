"""SR-001: benchmark Anthropic vision models against the eval manifest for skin classification."""
import argparse
import base64
import csv
import io
import json
import os
import time
from pathlib import Path

import anthropic
from PIL import Image

EXPERIMENTS_DIR = Path(__file__).resolve().parent
DEFAULT_MANIFEST = EXPERIMENTS_DIR / "eval_manifest.csv"
DEFAULT_OUTPUT = EXPERIMENTS_DIR / "results_api.csv"
MODEL_CHOICES = ["claude-sonnet-5", "claude-haiku-4-5"]
# Standard (non-introductory) per-MTok pricing, USD: {input, output}.
PRICING = {
    "claude-sonnet-5": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}
MAX_RETRIES = 3
FIELDNAMES = [
    "image_id", "model", "prompt_version", "true_label", "fitzpatrick_bucket",
    "pred_label", "referral_flag", "status", "latency_ms", "input_tokens", "output_tokens",
    "payload_kb", "raw_json",
]
# claude-haiku-4-5 wraps its JSON in ```json fences (the SR-001 parse_error cause); an assistant
# prefill of "{" forces raw JSON. claude-sonnet-5 rejects assistant prefills (400) and already emits
# clean JSON, so it is left unprefilled.
PREFILL_MODELS = {"claude-haiku-4-5"}
MAX_EDGE_PX = 1024  # resize longest edge to bound payload/latency; JPEG q90, in-memory only


def load_manifest(manifest_path):
    with manifest_path.open("r", newline="", encoding="utf-8") as f:
        return [{k.strip(): v for k, v in row.items()} for row in csv.DictReader(f)]


def call_with_retry(client, **kwargs):
    delay, last_exc = 1.0, None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return client.messages.create(**kwargs)
        except (anthropic.RateLimitError, anthropic.APIConnectionError) as exc:
            last_exc = exc
        except anthropic.APIStatusError as exc:
            if exc.status_code < 500:
                raise  # non-transient (4xx besides 429): don't retry
            last_exc = exc
        if attempt < MAX_RETRIES:
            time.sleep(delay)
            delay *= 2
    raise last_exc


def encode_resized_image(image_path):
    """Resize so the longest edge is <= MAX_EDGE_PX (LANCZOS, aspect preserved, skipped if already
    smaller), re-encode as JPEG q90 into an in-memory buffer, and return (base64_str, payload_kb).
    Never writes to disk."""
    with Image.open(image_path) as img:
        img = img.convert("RGB")  # flatten alpha/palette; JPEG has no alpha channel
        longest = max(img.size)
        if longest > MAX_EDGE_PX:
            scale = MAX_EDGE_PX / longest
            img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=90)
    payload = buffer.getvalue()
    return base64.standard_b64encode(payload).decode("utf-8"), len(payload) / 1024


def classify_image(client, model, prompt_text, image_path, prefill=""):
    data, payload_kb = encode_resized_image(image_path)
    messages = [{"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}},
        {"type": "text", "text": prompt_text},
    ]}]
    if prefill:
        messages.append({"role": "assistant", "content": prefill})  # force raw JSON output
    kwargs = dict(model=model, max_tokens=150, messages=messages)
    # claude-sonnet-5 rejects any non-default temperature (400); disable thinking instead to stay
    # fast and deterministic-ish. claude-haiku-4-5 still accepts temperature=0.
    if model == "claude-haiku-4-5":
        kwargs["temperature"] = 0
    else:
        kwargs["thinking"] = {"type": "disabled"}
    start = time.perf_counter()
    response = call_with_retry(client, **kwargs)
    return response, (time.perf_counter() - start) * 1000, payload_kb


def strip_json_fences(text):
    """Strip a leading ```json / ``` fence and trailing ``` plus surrounding whitespace."""
    text = text.strip()
    if text.startswith("```"):
        text = text[3:]
        if text[:4].lower() == "json":
            text = text[4:]
        text = text.strip()
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def parse_response(response, prefill=""):
    if response.stop_reason == "refusal":
        return "refusal", "", "", ""
    text = next((b.text for b in response.content if b.type == "text"), "")
    text = prefill + text  # reconstruct: the prefilled "{" is not echoed in response.content
    try:
        parsed = json.loads(strip_json_fences(text))
        return "ok", parsed.get("label", ""), parsed.get("referral_flag", ""), text
    except json.JSONDecodeError:
        return "parse_error", "", "", text


def classify_one(client, model, prompt_text, row):
    image_path = (EXPERIMENTS_DIR / Path(row["filepath"])).resolve()
    prefill = "{" if model in PREFILL_MODELS else ""
    try:
        response, latency_ms, payload_kb = classify_image(client, model, prompt_text, image_path, prefill)
        status, pred_label, referral_flag, raw_json = parse_response(response, prefill)
        input_tokens, output_tokens = response.usage.input_tokens, response.usage.output_tokens
    except Exception as exc:  # transient retries exhausted, or a non-retryable API error
        status, pred_label, referral_flag, raw_json = "api_error", "", "", str(exc)
        input_tokens, output_tokens, latency_ms, payload_kb = 0, 0, 0.0, 0.0
    return {
        "image_id": row["image_id"], "model": model, "true_label": row["true_label"],
        "fitzpatrick_bucket": row["fitzpatrick_bucket"], "pred_label": pred_label,
        "referral_flag": referral_flag, "status": status, "latency_ms": f"{latency_ms:.2f}",
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "payload_kb": f"{payload_kb:.2f}", "raw_json": raw_json,
    }


def run(client, model, prompt_version, rows, output_path):
    prompt_text = (EXPERIMENTS_DIR / f"prompt_v{prompt_version}.txt").read_text(encoding="utf-8")
    results = []
    for row in rows:
        result = classify_one(client, model, prompt_text, row)
        result["prompt_version"] = f"v{prompt_version}"
        results.append(result)
        print(f"{row['image_id']}: status={result['status']} pred={result['pred_label']}")
        time.sleep(1)  # sleep between calls
    if output_path is not None:
        append_results(output_path, results)
    return results


def append_results(output_path, results):
    """Append results, preserving existing rows. If the on-disk header predates the payload_kb
    column, migrate in place: rewrite the header and back-fill existing rows with a blank
    payload_kb (no data lost), then append the new rows."""
    existing_rows, existing_header = [], None
    if output_path.exists() and output_path.stat().st_size > 0:
        with output_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_header = reader.fieldnames
            existing_rows = list(reader)
    if existing_header == FIELDNAMES:  # header already current — plain append
        with output_path.open("a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=FIELDNAMES).writerows(results)
    else:  # new file, or older header missing payload_kb — rewrite with the full schema
        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(existing_rows)  # missing payload_kb -> blank (DictWriter restval)
            writer.writerows(results)


def print_cost_projection(model, results, total_rows):
    ok_results = [r for r in results if r["status"] != "api_error"]
    if not ok_results:
        print("No successful calls; cannot project cost.")
        return
    avg_input = sum(r["input_tokens"] for r in ok_results) / len(ok_results)
    avg_output = sum(r["output_tokens"] for r in ok_results) / len(ok_results)
    price = PRICING[model]
    cost_per_image = (avg_input / 1_000_000 * price["input"]) + (avg_output / 1_000_000 * price["output"])
    print(f"\nDry run: {len(results)} sampled, avg input={avg_input:.0f} tok, avg output={avg_output:.0f} tok")
    print(f"Projected cost for full manifest ({total_rows} images): ${cost_per_image * total_rows:.4f}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark an Anthropic vision model against the eval manifest.")
    parser.add_argument("--model", required=True, choices=MODEL_CHOICES)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--prompt-version", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true", help="Sample 2 images/class, project cost, and exit")
    args = parser.parse_args()

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    rows = load_manifest(args.manifest)

    if args.dry_run:
        sample, per_class = [], {}
        for row in rows:
            if per_class.get(row["true_label"], 0) < 2:
                sample.append(row)
                per_class[row["true_label"]] = per_class.get(row["true_label"], 0) + 1
        results = run(client, args.model, args.prompt_version, sample, output_path=None)
        print_cost_projection(args.model, results, len(rows))
        return

    run(client, args.model, args.prompt_version, rows, args.output)
    print(f"\nAppended {len(rows)} results to {args.output}")


if __name__ == "__main__":
    main()
