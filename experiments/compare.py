"""SR-001: compare local baseline vs Anthropic API results and write spike_report.md."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

EXPERIMENTS_DIR = Path(__file__).resolve().parent
DEFAULT_LOCAL = EXPERIMENTS_DIR / "results_local.csv"
DEFAULT_API = EXPERIMENTS_DIR / "results_api.csv"
DEFAULT_REPORT = EXPERIMENTS_DIR / "spike_report.md"
LABELS = ["Acne_Mild", "Acne_Severe", "Clear_Skin", "Hyperpigmentation"]
BUCKETS = ["I-III", "IV-VI"]
PRICING = {
    "claude-sonnet-5": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}
LATENCY_GATE_MS = 4000
ACCURACY_GATE_PP = 15


def load_csv(path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return [{k.strip(): v for k, v in row.items()} for row in csv.DictReader(f)]


def accuracy_by(rows, key, correct_fn):
    counts = defaultdict(lambda: [0, 0])  # [correct, total]
    for row in rows:
        counts[row[key]][1] += 1
        if correct_fn(row):
            counts[row[key]][0] += 1
    return counts


def fmt_fraction(correct, total):
    return f"{correct}/{total} ({(correct / total * 100) if total else 0.0:.1f}%)"


def confusion_matrix(rows, pred_key):
    matrix = defaultdict(lambda: defaultdict(int))
    for row in rows:
        matrix[row["true_label"]][row.get(pred_key, "")] += 1
    return matrix


def p95(values):
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))]


def render_confusion_table(matrix, pred_labels):
    lines = ["| true \\ pred | " + " | ".join(pred_labels) + " |", "|---" * (len(pred_labels) + 1) + "|"]
    for true_label in LABELS:
        cells = [str(matrix[true_label].get(p, 0)) for p in pred_labels]
        lines.append(f"| {true_label} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def accuracy_lines(by_class, by_bucket):
    lines = ["### Accuracy per class"]
    lines += [f"- {label}: {fmt_fraction(*by_class.get(label, [0, 0]))}" for label in LABELS]
    lines.append("\n### Accuracy per Fitzpatrick bucket")
    lines += [f"- {bucket}: {fmt_fraction(*by_bucket.get(bucket, [0, 0]))}" for bucket in BUCKETS]
    return lines


def local_section(rows):
    if not rows:
        return "## Local baseline (MobileNetV2)\n\nNo local results found.\n", {}
    correct = lambda r: r["pred_label"] == r["true_label"]
    by_class = accuracy_by(rows, "true_label", correct)
    by_bucket = accuracy_by(rows, "fitzpatrick_bucket", correct)
    lines = ["## Local baseline (MobileNetV2)\n"] + accuracy_lines(by_class, by_bucket)
    pred_labels = sorted({r["pred_label"] for r in rows} | set(LABELS))
    lines.append("\n### Confusion matrix\n")
    lines.append(render_confusion_table(confusion_matrix(rows, "pred_label"), pred_labels))
    latencies = [float(r["latency_ms"]) for r in rows if r["latency_ms"]]
    lines.append(f"\n### p95 latency: {p95(latencies):.1f} ms\n")
    return "\n".join(lines), by_bucket


def api_model_section(model, rows):
    ok_rows = [r for r in rows if r["status"] == "ok"]
    statuses = defaultdict(int)
    for r in rows:
        statuses[r["status"]] += 1
    total = len(rows)
    correct = lambda r: r["status"] == "ok" and r["pred_label"] == r["true_label"]
    by_class = accuracy_by(rows, "true_label", correct)
    by_bucket = accuracy_by(rows, "fitzpatrick_bucket", correct)

    lines = [f"## API — {model}\n", "### Status breakdown"]
    lines += [f"- {status}: {fmt_fraction(count, total)}" for status, count in sorted(statuses.items())]
    lines += [""] + accuracy_lines(by_class, by_bucket)

    pred_labels = sorted({r["pred_label"] for r in ok_rows} | set(LABELS) | {"Uncertain_Refer"})
    lines.append("\n### Confusion matrix (status=ok only)\n")
    lines.append(render_confusion_table(confusion_matrix(ok_rows, "pred_label"), pred_labels))

    latencies = [float(r["latency_ms"]) for r in rows if r["latency_ms"]]
    p95_latency = p95(latencies)
    lines.append(f"\n### p95 latency: {p95_latency:.1f} ms\n")

    if ok_rows and model in PRICING:
        avg_in = sum(int(r["input_tokens"]) for r in ok_rows) / len(ok_rows)
        avg_out = sum(int(r["output_tokens"]) for r in ok_rows) / len(ok_rows)
        price = PRICING[model]
        cost_100 = ((avg_in / 1_000_000 * price["input"]) + (avg_out / 1_000_000 * price["output"])) * 100
        lines.append(f"### Cost per 100 inferences: ${cost_100:.2f}\n")
    else:
        lines.append("### Cost per 100 inferences: n/a (no successful calls)\n")
    return "\n".join(lines), by_bucket, p95_latency, statuses, total


def gate_verdict(model, api_by_bucket, local_by_bucket, p95_latency, statuses, total):
    api_c, api_t = api_by_bucket.get("IV-VI", [0, 0])
    local_c, local_t = local_by_bucket.get("IV-VI", [0, 0])
    api_pct = (api_c / api_t * 100) if api_t else 0.0
    local_pct = (local_c / local_t * 100) if local_t else 0.0
    delta = api_pct - local_pct
    accuracy_ok = delta >= ACCURACY_GATE_PP
    latency_ok = p95_latency < LATENCY_GATE_MS
    all_ok = total > 0 and statuses.get("ok", 0) == total
    passed = accuracy_ok and latency_ok and all_ok
    return "\n".join([
        f"## SR-001 gate — {model}\n",
        f"- IV-VI accuracy: API {api_pct:.1f}% vs local {local_pct:.1f}% "
        f"(delta {delta:+.1f}pp, need >= {ACCURACY_GATE_PP}pp): {'PASS' if accuracy_ok else 'FAIL'}",
        f"- p95 latency {p95_latency:.1f}ms < {LATENCY_GATE_MS}ms: {'PASS' if latency_ok else 'FAIL'}",
        f"- 100% status=ok on final prompt version: {'PASS' if all_ok else 'FAIL'}",
        f"\n**Verdict: {'PASS' if passed else 'FAIL'}**\n",
    ])


def main():
    parser = argparse.ArgumentParser(description="Compare local baseline vs API results and write spike_report.md.")
    parser.add_argument("--local-results", type=Path, default=DEFAULT_LOCAL)
    parser.add_argument("--api-results", type=Path, default=DEFAULT_API)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    local_rows = load_csv(args.local_results)
    api_rows = load_csv(args.api_results)
    local_text, local_by_bucket = local_section(local_rows)
    sections = ["# SR-001 API Feasibility Spike Report\n", local_text]

    for model in sorted({r["model"] for r in api_rows}):
        model_rows = [r for r in api_rows if r["model"] == model]
        final_version = max(int(r["prompt_version"]) for r in model_rows)
        final_rows = [r for r in model_rows if int(r["prompt_version"]) == final_version]
        section_text, by_bucket, p95_latency, statuses, total = api_model_section(model, final_rows)
        sections.append(section_text)
        sections.append(gate_verdict(model, by_bucket, local_by_bucket, p95_latency, statuses, total))

    args.output.write_text("\n".join(sections), encoding="utf-8")
    print(f"Wrote report to {args.output}")


if __name__ == "__main__":
    main()
