"""SR-001: ingest raw staging images into eval_set and append rows to eval_manifest.csv."""
import argparse
import csv
from pathlib import Path

from PIL import Image, ImageOps

EXPERIMENTS_DIR = Path(__file__).resolve().parent
RAW_STAGING_DIR = EXPERIMENTS_DIR / "raw_staging"
EVAL_SET_DIR = EXPERIMENTS_DIR / "eval_set"
MANIFEST_PATH = EXPERIMENTS_DIR / "eval_manifest.csv"
FIELDNAMES = ["image_id", "filepath", "true_label", "fitzpatrick_bucket", "source", "notes"]
ALLOWED_LABELS = ["Acne_Mild", "Acne_Severe", "Clear_Skin", "Hyperpigmentation"]


def load_manifest_rows():
    if not MANIFEST_PATH.exists() or MANIFEST_PATH.stat().st_size == 0:
        return []
    with MANIFEST_PATH.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [{k.strip(): v for k, v in row.items()} for row in reader]


def highest_existing_id(rows):
    max_n = 0
    for row in rows:
        stem = Path(row.get("filepath", "")).stem
        if stem.startswith("eval_"):
            try:
                max_n = max(max_n, int(stem.rsplit("_", 1)[1]))
            except (IndexError, ValueError):
                continue
    return max_n


def strip_exif_and_save(src_path, dest_path):
    with Image.open(src_path) as img:
        img = ImageOps.exif_transpose(img)  # bake in orientation before dropping metadata
        img = img.convert("RGB")
        clean = Image.frombytes(img.mode, img.size, img.tobytes())  # drops EXIF/info dict
        clean.save(dest_path, "JPEG")


def main():
    parser = argparse.ArgumentParser(
        description="Copy raw_staging images into eval_set, strip EXIF, and append manifest rows."
    )
    parser.add_argument("--source", required=True, help="Value recorded in the manifest 'source' column")
    args = parser.parse_args()

    rows = load_manifest_rows()
    next_id = highest_existing_id(rows) + 1
    already_ingested = {row["notes"] for row in rows if row.get("notes", "").startswith("orig:")}

    new_rows = []
    for class_dir in sorted(RAW_STAGING_DIR.iterdir()):
        if not class_dir.is_dir() or class_dir.name not in ALLOWED_LABELS:
            continue
        label = class_dir.name
        dest_dir = EVAL_SET_DIR / label
        dest_dir.mkdir(parents=True, exist_ok=True)
        for src_path in sorted(class_dir.iterdir()):
            if not src_path.is_file():
                continue
            origin_note = f"orig:{label}/{src_path.name}"
            if origin_note in already_ingested:
                continue  # idempotent: this raw file was already ingested in a prior run
            image_id = f"eval_{next_id:03d}"
            dest_path = dest_dir / f"{image_id}.jpg"
            strip_exif_and_save(src_path, dest_path)
            rel_path = dest_path.relative_to(EXPERIMENTS_DIR).as_posix()
            new_rows.append([image_id, rel_path, label, "", args.source, origin_note])
            already_ingested.add(origin_note)
            next_id += 1

    if new_rows:
        write_header = not MANIFEST_PATH.exists() or MANIFEST_PATH.stat().st_size == 0
        with MANIFEST_PATH.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(FIELDNAMES)
            writer.writerows(new_rows)

    print(f"Ingested {len(new_rows)} new image(s) into eval_set; manifest updated at {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
