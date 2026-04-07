#!/usr/bin/env python3
"""
Convert user corrections into Tesseract LSTM training data.

Reads correction JSON files from backend/data/corrections/,
crops image regions using bounding boxes, pairs them with corrected text,
and produces .box + .lstmf files for fine-tuning.
"""

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

CORRECTIONS_DIR = Path(__file__).resolve().parents[1] / "backend" / "data" / "corrections"
UPLOADS_DIR = Path(__file__).resolve().parents[1] / "backend" / "data" / "uploads"
OUTPUT_DIR = Path(__file__).resolve().parent / "training_data"
GROUND_TRUTH_DIR = OUTPUT_DIR / "ground_truth"
LSTMF_DIR = OUTPUT_DIR / "lstmf"


def find_upload_image(image_id: str) -> Path | None:
    for ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"):
        p = UPLOADS_DIR / f"{image_id}{ext}"
        if p.exists():
            return p
    return None


def crop_word_region(img: Image.Image, bbox: dict, padding: int = 2) -> Image.Image:
    x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
    left = max(0, x - padding)
    top = max(0, y - padding)
    right = min(img.width, x + w + padding)
    bottom = min(img.height, y + h + padding)
    return img.crop((left, top, right, bottom))


def generate_box_file(image_path: Path, text: str, box_path: Path):
    """Generate a Tesseract .box file for a single-line image."""
    img = Image.open(image_path)
    w, h = img.size

    lines = []
    for ch in text:
        if ch == " ":
            continue
        lines.append(f"{ch} 0 0 {w} {h} 0")

    box_path.write_text("\n".join(lines) + "\n")


def generate_lstmf(tif_path: Path, box_path: Path, lang: str = "eng"):
    """Run tesseract to produce .lstmf from .tif + .box pair."""
    base = tif_path.with_suffix("")
    cmd = [
        "tesseract", str(tif_path), str(base),
        "--psm", "7",
        "lstm.train",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Warning: tesseract lstm.train failed for {tif_path.name}: {result.stderr.strip()}")
        return None

    lstmf = base.with_suffix(".lstmf")
    if lstmf.exists():
        return lstmf
    return None


def process_correction(correction: dict, idx: int):
    """Process a single correction record into training data."""
    image_id = correction["image_id"]
    img_path = find_upload_image(image_id)
    if not img_path:
        print(f"  Skipping: upload image not found for {image_id}")
        return []

    img = Image.open(img_path)
    lstmf_files = []

    word_corrections = correction.get("word_corrections", [])
    if not word_corrections:
        # Full-page training: use the entire image with corrected text
        name = f"page_{idx:05d}"
        tif_path = GROUND_TRUTH_DIR / f"{name}.tif"
        box_path = GROUND_TRUTH_DIR / f"{name}.box"
        gt_path = GROUND_TRUTH_DIR / f"{name}.gt.txt"

        img.save(str(tif_path))
        gt_path.write_text(correction["corrected_text"])
        generate_box_file(tif_path, correction["corrected_text"], box_path)

        lstmf = generate_lstmf(tif_path, box_path)
        if lstmf:
            lstmf_files.append(lstmf)
    else:
        for j, wc in enumerate(word_corrections):
            name = f"word_{idx:05d}_{j:03d}"
            crop = crop_word_region(img, wc["bbox"])

            tif_path = GROUND_TRUTH_DIR / f"{name}.tif"
            box_path = GROUND_TRUTH_DIR / f"{name}.box"
            gt_path = GROUND_TRUTH_DIR / f"{name}.gt.txt"

            crop.save(str(tif_path))
            gt_path.write_text(wc["corrected"])
            generate_box_file(tif_path, wc["corrected"], box_path)

            lstmf = generate_lstmf(tif_path, box_path)
            if lstmf:
                lstmf_files.append(lstmf)

    return lstmf_files


def main():
    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)
    LSTMF_DIR.mkdir(parents=True, exist_ok=True)

    correction_files = sorted(CORRECTIONS_DIR.glob("*.json"))
    if not correction_files:
        print("No corrections found. Submit corrections through the web UI first.")
        sys.exit(0)

    print(f"Found {len(correction_files)} correction(s)")
    all_lstmf = []

    for idx, cfile in enumerate(correction_files):
        correction = json.loads(cfile.read_text())
        print(f"Processing [{idx + 1}/{len(correction_files)}]: {cfile.name}")
        lstmfs = process_correction(correction, idx)
        all_lstmf.extend(lstmfs)

    # Write training file list
    train_list = OUTPUT_DIR / "training_files.txt"
    train_list.write_text("\n".join(str(f) for f in all_lstmf) + "\n")
    print(f"\nGenerated {len(all_lstmf)} .lstmf training file(s)")
    print(f"Training list written to: {train_list}")


if __name__ == "__main__":
    main()
