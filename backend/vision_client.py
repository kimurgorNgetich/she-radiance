"""backend/vision_client.py — SR-002: Anthropic vision API client for skin-condition triage.

Replaces the local CNN (backend/inference.py) with a call to Claude's vision API. Ports the
resize/base64/prefill/fence-stripping logic validated in experiments/api_spike.py (SR-001).
"""
import base64
import io
import json
import sys
import time
from pathlib import Path

import anthropic
from PIL import Image

from config import get_secret

BACKEND_DIR = Path(__file__).resolve().parent
PROMPT_PATH = BACKEND_DIR / "prompt.txt"
PROMPT_VERSION = "v2"

DEFAULT_MODEL = "claude-haiku-4-5"
MAX_EDGE_PX = 1024  # resize longest edge to bound payload/latency; JPEG q90, in-memory only
MAX_TOKENS = 150
TEMPERATURE = 0
MAX_RETRIES = 3


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _encode_resized_image(image_path: Path) -> str:
    """Resize so the longest edge is <= MAX_EDGE_PX (LANCZOS, aspect preserved, skipped if
    already smaller), re-encode as JPEG q90 into an in-memory buffer, and return the base64
    string. Never writes to disk."""
    with Image.open(image_path) as img:
        img = img.convert("RGB")  # flatten alpha/palette; JPEG has no alpha channel
        longest = max(img.size)
        if longest > MAX_EDGE_PX:
            scale = MAX_EDGE_PX / longest
            img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=90)
    return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")


def _strip_json_fences(text: str) -> str:
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


def _call_with_retry(client, **kwargs):
    """Exponential backoff on transient/rate-limit errors only; auth errors are never retried."""
    delay, last_exc = 1.0, None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return client.messages.create(**kwargs)
        except anthropic.AuthenticationError:
            raise  # never retry auth errors
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


def _fail_closed(model: str, latency_ms: float, status: str) -> dict:
    return {
        "condition": "Uncertain_Refer",
        "referral_flag": True,
        "visible_features": [],
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "latency_ms": latency_ms,
        "status": status,
    }


def analyze_selfie(image_path: str, model: str = DEFAULT_MODEL) -> dict:
    """SR-002: classify a selfie's visible skin condition via the Anthropic vision API.

    Never raises to the caller. On any failure — missing/invalid credentials, a transient or
    non-transient API error, a safety refusal, or a response that doesn't parse as the expected
    JSON shape — returns condition="Uncertain_Refer" with referral_flag=True (fail closed).

    Returns a dict with keys: condition, referral_flag, visible_features, model,
    prompt_version, latency_ms, status. status is one of:
    ok | parse_error | refusal | api_error | auth_error.
    """
    start = time.perf_counter()

    api_key = get_secret("ANTHROPIC_API_KEY")
    if not api_key:
        return _fail_closed(model, (time.perf_counter() - start) * 1000, "auth_error")

    try:
        prompt_text = _load_prompt()
        image_data = _encode_resized_image(Path(image_path))
    except Exception:
        return _fail_closed(model, (time.perf_counter() - start) * 1000, "api_error")

    client = anthropic.Anthropic(api_key=api_key)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}},
                {"type": "text", "text": prompt_text},
            ],
        },
        {"role": "assistant", "content": "{"},  # forces raw JSON output, no markdown fences
    ]

    try:
        response = _call_with_retry(
            client, model=model, max_tokens=MAX_TOKENS, temperature=TEMPERATURE, messages=messages
        )
    except anthropic.AuthenticationError:
        return _fail_closed(model, (time.perf_counter() - start) * 1000, "auth_error")
    except Exception:
        return _fail_closed(model, (time.perf_counter() - start) * 1000, "api_error")

    latency_ms = (time.perf_counter() - start) * 1000

    if response.stop_reason == "refusal":
        return _fail_closed(model, latency_ms, "refusal")

    text = next((b.text for b in response.content if b.type == "text"), "")
    text = "{" + text  # reconstruct: the prefilled "{" is not echoed in response.content

    try:
        parsed = json.loads(_strip_json_fences(text))
        condition = parsed["label"]
        referral_flag = parsed["referral_flag"]
        visible_features = parsed.get("visible_features", [])
    except (json.JSONDecodeError, KeyError, TypeError):
        return _fail_closed(model, latency_ms, "parse_error")

    return {
        "condition": condition,
        "referral_flag": referral_flag,
        "visible_features": visible_features,
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "latency_ms": latency_ms,
        "status": "ok",
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python vision_client.py <image_path>")
        sys.exit(1)
    print(analyze_selfie(sys.argv[1]))
