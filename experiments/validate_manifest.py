"""SR-001: validate eval_manifest.csv and the eval image set, printing a PASS/FAIL report."""
import argparse
import csv
import hashlib
from pathlib import Path

from PIL import Image, UnidentifiedImageError

EXPERIMENTS_DIR = Path(__file__).resolve().parent
DEFAULT_MANIFEST = EXPERIMENTS_DIR / "eval_manifest.csv"
CONTAMINATION_DIRS = [EXPERIMENTS_DIR.parent / "AI_TRAINING_DATA", EXPERIMENTS_DIR / "data_reserve"]
ALLOWED_LABELS = {"Acne_Mild", "Acne_Severe", "Clear_Skin", "Hyperpigmentation"}
ALLOWED_BUCKETS = {"I-III", "IV-VI"}
MIN_CELL_COUNT = 6


def load_manifest(manifest_path):
    with manifest_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [{k.strip(): (v.strip() if v else v) for k, v in row.items()} for row in reader]


def md5_of(path):
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_contamination_hashes():
    hashes = {}
    for base in CONTAMINATION_DIRS:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file():
                hashes.setdefault(md5_of(path), []).append(path)
    return hashes


def main():
    parser = argparse.ArgumentParser(description="Validate eval_manifest.csv integrity (PASS/FAIL report).")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Path to eval_manifest.csv")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"FAIL: manifest not found at {manifest_path}")
        raise SystemExit(1)

    rows = load_manifest(manifest_path)
    failures = []
    seen_ids = set()
    cell_counts = {(label, bucket): 0 for label in ALLOWED_LABELS for bucket in ALLOWED_BUCKETS}

    for row in rows:
        image_id = row.get("image_id", "")
        filepath = row.get("filepath", "")
        true_label = row.get("true_label", "")
        bucket = row.get("fitzpatrick_bucket", "")

        if not image_id:
            failures.append("blank image_id in a row")
        elif image_id in seen_ids:
            failures.append(f"duplicate image_id: {image_id}")
        seen_ids.add(image_id)

        if not filepath:
            failures.append(f"{image_id}: blank filepath")
        else:
            resolved = (EXPERIMENTS_DIR / Path(filepath)).resolve()
            if not resolved.exists():
                failures.append(f"{image_id}: filepath does not exist ({filepath})")
            else:
                try:
                    with Image.open(resolved) as img:
                        img.verify()
                except (UnidentifiedImageError, OSError) as exc:
                    failures.append(f"{image_id}: failed to open with PIL ({exc})")

        if true_label not in ALLOWED_LABELS:
            failures.append(f"{image_id}: invalid true_label '{true_label}'")
        if bucket not in ALLOWED_BUCKETS:
            failures.append(f"{image_id}: invalid fitzpatrick_bucket '{bucket}'")
        if true_label in ALLOWED_LABELS and bucket in ALLOWED_BUCKETS:
            cell_counts[(true_label, bucket)] += 1

    print("Per-cell counts (class x fitzpatrick bucket):")
    for label in sorted(ALLOWED_LABELS):
        for bucket in sorted(ALLOWED_BUCKETS):
            count = cell_counts[(label, bucket)]
            marker = "FAIL" if count < MIN_CELL_COUNT else "OK"
            print(f"  {label:20s} {bucket:6s} {count:3d}  [{marker}]")
            if count < MIN_CELL_COUNT:
                failures.append(f"cell ({label}, {bucket}) has {count} images, minimum is {MIN_CELL_COUNT}")

    print("\nChecking for training-data contamination (MD5)...")
    contamination_hashes = collect_contamination_hashes()
    if contamination_hashes:
        for row in rows:
            filepath = row.get("filepath", "")
            if not filepath:
                continue
            resolved = (EXPERIMENTS_DIR / Path(filepath)).resolve()
            if resolved.exists():
                digest = md5_of(resolved)
                if digest in contamination_hashes:
                    matches = ", ".join(str(p) for p in contamination_hashes[digest])
                    failures.append(f"{row.get('image_id')}: byte-identical to training data ({matches})")
    else:
        print("  no files found under contamination directories; skipping")

    print()
    if failures:
        print(f"FAIL ({len(failures)} issue(s)):")
        for f in failures:
            print(f"  - {f}")
        raise SystemExit(1)

    print("PASS: manifest and eval set are valid.")


if __name__ == "__main__":
    main()
