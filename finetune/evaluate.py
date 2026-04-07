#!/usr/bin/env python3
"""
Evaluate fine-tuned Tesseract model against the base model.

Measures Character Error Rate (CER) and Word Error Rate (WER)
using held-out correction data as ground truth.
"""

import json
import subprocess
import sys
from pathlib import Path

CORRECTIONS_DIR = Path(__file__).resolve().parents[1] / "backend" / "data" / "corrections"
UPLOADS_DIR = Path(__file__).resolve().parents[1] / "backend" / "data" / "uploads"
MODEL_DIR = Path(__file__).resolve().parent / "model"


def find_upload_image(image_id: str) -> Path | None:
    for ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"):
        p = UPLOADS_DIR / f"{image_id}{ext}"
        if p.exists():
            return p
    return None


def run_tesseract(image_path: str, tessdata: str = "", lang: str = "eng") -> str:
    cmd = ["tesseract", image_path, "stdout", "-l", lang]
    if tessdata:
        cmd.extend(["--tessdata-dir", tessdata])
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()


def edit_distance(s1: str, s2: str) -> int:
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1,
                           dp[i - 1][j - 1] + cost)
    return dp[m][n]


def compute_cer(predicted: str, ground_truth: str) -> float:
    if not ground_truth:
        return 0.0 if not predicted else 1.0
    return edit_distance(predicted, ground_truth) / len(ground_truth)


def compute_wer(predicted: str, ground_truth: str) -> float:
    gt_words = ground_truth.split()
    if not gt_words:
        return 0.0 if not predicted.split() else 1.0
    pred_words = predicted.split()
    return edit_distance(
        " ".join(pred_words), " ".join(gt_words)
    ) / len(" ".join(gt_words))


def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else "eng"
    finetuned_dir = str(MODEL_DIR)
    finetuned_model = MODEL_DIR / f"{lang}_finetuned.traineddata"

    if not finetuned_model.exists():
        print(f"Fine-tuned model not found: {finetuned_model}")
        print("Run train.sh first.")
        sys.exit(1)

    correction_files = sorted(CORRECTIONS_DIR.glob("*.json"))
    if not correction_files:
        print("No corrections found for evaluation.")
        sys.exit(0)

    # Use last 20% as validation set (or at least 1)
    val_count = max(1, len(correction_files) // 5)
    val_files = correction_files[-val_count:]

    print(f"Evaluating {len(val_files)} sample(s)")
    print(f"Base model: {lang}")
    print(f"Fine-tuned model: {finetuned_model.name}")
    print("=" * 60)

    base_cer_total = 0.0
    ft_cer_total = 0.0
    base_wer_total = 0.0
    ft_wer_total = 0.0
    count = 0

    for cfile in val_files:
        correction = json.loads(cfile.read_text())
        img_path = find_upload_image(correction["image_id"])
        if not img_path:
            continue

        ground_truth = correction["corrected_text"].strip()

        base_text = run_tesseract(str(img_path), lang=lang)
        ft_text = run_tesseract(str(img_path), tessdata=finetuned_dir,
                                lang=f"{lang}_finetuned")

        base_cer = compute_cer(base_text, ground_truth)
        ft_cer = compute_cer(ft_text, ground_truth)
        base_wer = compute_wer(base_text, ground_truth)
        ft_wer = compute_wer(ft_text, ground_truth)

        base_cer_total += base_cer
        ft_cer_total += ft_cer
        base_wer_total += base_wer
        ft_wer_total += ft_wer
        count += 1

        print(f"\nImage: {img_path.name}")
        print(f"  Base CER: {base_cer:.4f}  Fine-tuned CER: {ft_cer:.4f}")
        print(f"  Base WER: {base_wer:.4f}  Fine-tuned WER: {ft_wer:.4f}")

    if count == 0:
        print("No images found for evaluation.")
        return

    print("\n" + "=" * 60)
    print(f"Average over {count} sample(s):")
    print(f"  Base model     CER: {base_cer_total / count:.4f}  WER: {base_wer_total / count:.4f}")
    print(f"  Fine-tuned     CER: {ft_cer_total / count:.4f}  WER: {ft_wer_total / count:.4f}")

    cer_improvement = (base_cer_total - ft_cer_total) / max(base_cer_total, 1e-9) * 100
    wer_improvement = (base_wer_total - ft_wer_total) / max(base_wer_total, 1e-9) * 100
    print(f"  CER improvement: {cer_improvement:+.1f}%")
    print(f"  WER improvement: {wer_improvement:+.1f}%")


if __name__ == "__main__":
    main()
