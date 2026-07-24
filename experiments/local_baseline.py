"""SR-001: run the local MobileNetV2 classifier over the eval manifest and record predictions."""
import argparse
import csv
import sys
import time
from pathlib import Path

EXPERIMENTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = EXPERIMENTS_DIR.parent / "backend"
DEFAULT_MANIFEST = EXPERIMENTS_DIR / "eval_manifest.csv"
DEFAULT_OUTPUT = EXPERIMENTS_DIR / "results_local.csv"

sys.path.insert(0, str(BACKEND_DIR))


def load_manifest(manifest_path):
    with manifest_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [{k.strip(): v for k, v in row.items()} for row in reader]


def main():
    parser = argparse.ArgumentParser(description="Run the local classifier over the eval manifest.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Path to eval_manifest.csv")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Path to write results_local.csv")
    args = parser.parse_args()

    from inference import analyze_user_selfie  # backend/inference.py, loads the model at import time

    rows = load_manifest(args.manifest)

    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["image_id", "true_label", "fitzpatrick_bucket", "pred_label", "confidence", "latency_ms"])
        for row in rows:
            image_path = (EXPERIMENTS_DIR / Path(row["filepath"])).resolve()
            start = time.perf_counter()
            confidence, pred_label = analyze_user_selfie(str(image_path))
            latency_ms = (time.perf_counter() - start) * 1000
            writer.writerow([
                row["image_id"],
                row["true_label"],
                row["fitzpatrick_bucket"],
                pred_label,
                f"{confidence:.4f}",
                f"{latency_ms:.2f}",
            ])
            print(f"{row['image_id']}: pred={pred_label} conf={confidence:.2f} latency={latency_ms:.1f}ms")

    print(f"\nWrote {len(rows)} results to {args.output}")


if __name__ == "__main__":
    main()
