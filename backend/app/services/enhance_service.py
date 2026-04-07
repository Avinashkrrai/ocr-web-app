"""Image enhancement for old/degraded documents.

Applies contrast stretching, sharpening, and optional grayscale conversion
to make faded text more readable before OCR.
"""

import logging
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

logger = logging.getLogger(__name__)


def enhance_document(image_path: str, strength: str = "auto") -> str:
    """Enhance an old/degraded document image for better OCR.

    Returns the path to the enhanced image (saved alongside the original).
    """
    src = Path(image_path)
    dst = src.with_stem(src.stem + "_enhanced")

    img = Image.open(src)
    original_mode = img.mode

    # Work in RGB for consistent processing
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # 1. Auto-contrast: stretches the histogram so faded ink becomes dark
    img = ImageOps.autocontrast(img, cutoff=2)

    # 2. Increase contrast further for very faded documents
    factor = {"light": 1.3, "medium": 1.6, "heavy": 2.0, "auto": 1.5}[strength]
    img = ImageEnhance.Contrast(img).enhance(factor)

    # 3. Slight brightness boost (old papers tend to be dark after contrast)
    img = ImageEnhance.Brightness(img).enhance(1.05)

    # 4. Sharpen to clarify blurred characters
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageEnhance.Sharpness(img).enhance(1.8)

    # 5. Convert to grayscale to remove yellowing/browning
    if original_mode != "L":
        img = img.convert("L")

    img.save(str(dst), quality=95)
    logger.info("Enhanced %s → %s (strength=%s)", src.name, dst.name, strength)
    return str(dst)
