import re
import sys
import os
from pathlib import Path

engine_path = str(Path(__file__).resolve().parents[3] / "engine" / "build")
if engine_path not in sys.path:
    sys.path.insert(0, engine_path)

import ocr_engine

_engine: ocr_engine.OCREngine | None = None


def get_engine() -> ocr_engine.OCREngine:
    global _engine
    if _engine is None:
        _engine = ocr_engine.OCREngine()
        datapath = os.environ.get("TESSDATA_PREFIX", "")
        lang = os.environ.get("OCR_LANG", "eng")
        if not _engine.init(lang, datapath):
            raise RuntimeError(f"Failed to initialize Tesseract with lang={lang}")
    return _engine


def reflow_text(raw: str) -> str:
    """
    Merge wrapped lines into proper paragraphs.

    Tesseract preserves hard line breaks from the page layout, so a sentence
    like "detect and\\nclassify" appears as two lines.  This function joins
    lines that belong to the same paragraph while keeping real paragraph
    breaks (blank lines) and intentional short lines (headings, list items).
    """
    # Normalise line endings
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")

    # Split into paragraph blocks separated by one or more blank lines
    blocks = re.split(r"\n{2,}", raw)

    reflowed = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        if len(lines) == 1:
            reflowed.append(lines[0])
            continue

        merged_parts: list[str] = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            if not merged_parts:
                merged_parts.append(stripped)
                continue

            prev = merged_parts[-1]

            # Heuristics for when to JOIN with the previous line:
            #  - Previous line does NOT end with sentence-ending punctuation
            #  - Current line starts with a lowercase letter
            #  - Previous line is reasonably long (> 35 chars = likely a wrapped line)
            ends_sentence = prev and prev[-1] in ".!?:\u2026"
            starts_lower = stripped[0].islower()
            prev_is_long = len(prev) > 35

            if not ends_sentence and (starts_lower or prev_is_long):
                # Join: continuation of the same paragraph line
                merged_parts[-1] = prev + " " + stripped
            else:
                # Keep as a separate line (heading, list item, etc.)
                merged_parts.append(stripped)

        reflowed.append("\n".join(merged_parts))

    return "\n\n".join(reflowed)


def run_ocr(image_path: str) -> dict:
    engine = get_engine()
    result = engine.process_image(image_path)
    return {
        "full_text": reflow_text(result.full_text),
        "words": [
            {
                "text": w.text,
                "confidence": w.confidence,
                "bbox": {"x": w.bbox.x, "y": w.bbox.y,
                         "w": w.bbox.w, "h": w.bbox.h},
            }
            for w in result.words
        ],
        "blocks": [
            {
                "text": b.text,
                "bbox": {"x": b.bbox.x, "y": b.bbox.y,
                         "w": b.bbox.w, "h": b.bbox.h},
            }
            for b in result.blocks
        ],
    }
