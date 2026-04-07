import uuid
import shutil
import asyncio
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

import fitz  # PyMuPDF

from ..services.ocr_service import run_ocr
from ..models.schemas import OCRResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ocr"])

UPLOADS_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/tiff", "image/bmp", "image/webp"}
ALLOWED_PDF_TYPES = {"application/pdf"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_PDF_TYPES


def pdf_to_images(pdf_path: Path, output_dir: Path, image_id: str) -> list[Path]:
    """Convert each PDF page to a PNG image. Returns list of image paths."""
    doc = fitz.open(str(pdf_path))
    image_paths = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=200)
        img_path = output_dir / f"{image_id}_page_{page_num + 1}.png"
        pix.save(str(img_path))
        image_paths.append(img_path)
    doc.close()
    return image_paths


@router.post("/ocr", response_model=OCRResponse)
async def perform_ocr(file: UploadFile = File(...)):
    content_type = file.content_type or ""

    if content_type not in ALLOWED_TYPES:
        ext = Path(file.filename or "").suffix.lower()
        if ext == ".pdf":
            content_type = "application/pdf"
        elif ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"):
            content_type = f"image/{ext.lstrip('.')}"
        else:
            raise HTTPException(
                400, "File must be an image (PNG, JPG, TIFF, BMP) or a PDF"
            )

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    image_id = str(uuid.uuid4())
    ext = Path(file.filename or "file.png").suffix or ".png"
    save_path = UPLOADS_DIR / f"{image_id}{ext}"

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    is_pdf = content_type in ALLOWED_PDF_TYPES or ext.lower() == ".pdf"

    try:
        if is_pdf:
            logger.info("Converting PDF to images…")
            page_images = await asyncio.to_thread(
                pdf_to_images, save_path, UPLOADS_DIR, image_id
            )
            if not page_images:
                raise HTTPException(400, "PDF has no pages")

            all_text = []
            all_words = []
            all_blocks = []

            for i, page_img in enumerate(page_images):
                logger.info("OCR page %d/%d", i + 1, len(page_images))
                result = await asyncio.to_thread(run_ocr, str(page_img))
                all_text.append(result["full_text"])
                all_words.extend(result["words"])
                all_blocks.extend(result["blocks"])

            full_text = "\n\n".join(all_text)
            preview_filename = f"{image_id}_page_1.png"
            page_count = len(page_images)
        else:
            logger.info("Running OCR on image…")
            result = await asyncio.to_thread(run_ocr, str(save_path))
            full_text = result["full_text"]
            all_words = result["words"]
            all_blocks = result["blocks"]
            preview_filename = f"{image_id}{ext}"
            page_count = 1

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("OCR failed")
        raise HTTPException(500, f"OCR processing failed: {e}")

    logger.info("OCR complete: %d pages, %d words", page_count, len(all_words))

    return OCRResponse(
        image_id=image_id,
        full_text=full_text,
        words=all_words,
        blocks=all_blocks,
        page_count=page_count,
        preview_url=f"/uploads/{preview_filename}",
        is_pdf=is_pdf,
        original_pdf_url=f"/uploads/{image_id}{ext}" if is_pdf else None,
    )
