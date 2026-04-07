import os
import uuid
import shutil
import asyncio
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Query, HTTPException

import fitz  # PyMuPDF

from ..services.ocr_service import run_ocr
from ..services.gemini_service import run_gemini_ocr
from ..models.schemas import OCRResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ocr"])

UPLOADS_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/tiff", "image/bmp", "image/webp"}
ALLOWED_PDF_TYPES = {"application/pdf"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_PDF_TYPES


def pdf_to_images(pdf_path: Path, output_dir: Path, image_id: str) -> list[Path]:
    """Convert each PDF page to a PNG image (for Tesseract or preview)."""
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


@router.get("/engines")
async def list_engines():
    """Return available OCR engines so the frontend can show the selector."""
    engines = [{"id": "tesseract", "name": "Tesseract OCR"}]
    if os.environ.get("GEMINI_API_KEY"):
        engines.insert(0, {"id": "gemini", "name": "Gemini 2.5 Flash"})
    default = engines[0]["id"]
    return {"engines": engines, "default": default}


@router.post("/ocr", response_model=OCRResponse)
async def perform_ocr(
    file: UploadFile = File(...),
    engine: str = Query("auto"),
):
    # ── resolve engine ──────────────────────────────────────────────
    if engine == "auto":
        engine = "gemini" if os.environ.get("GEMINI_API_KEY") else "tesseract"
    if engine not in ("gemini", "tesseract"):
        raise HTTPException(400, f"Unknown engine: {engine}")

    # ── validate file type ──────────────────────────────────────────
    content_type = file.content_type or ""
    if content_type not in ALLOWED_TYPES:
        ext = Path(file.filename or "").suffix.lower()
        if ext == ".pdf":
            content_type = "application/pdf"
        elif ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"):
            content_type = f"image/{ext.lstrip('.')}"
        else:
            raise HTTPException(400, "File must be an image (PNG, JPG, TIFF, BMP) or a PDF")

    # ── save upload ─────────────────────────────────────────────────
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    image_id = str(uuid.uuid4())
    ext = Path(file.filename or "file.png").suffix or ".png"
    save_path = UPLOADS_DIR / f"{image_id}{ext}"

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    is_pdf = content_type in ALLOWED_PDF_TYPES or ext.lower() == ".pdf"

    # ── run OCR ─────────────────────────────────────────────────────
    try:
        if engine == "gemini":
            result = await _ocr_gemini(save_path, is_pdf, image_id)
        else:
            result = await _ocr_tesseract(save_path, is_pdf, image_id, ext)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("OCR failed (engine=%s)", engine)
        raise HTTPException(500, f"OCR processing failed: {e}")

    full_text = result["full_text"]
    all_words = result["words"]
    all_blocks = result["blocks"]
    page_count = result["page_count"]
    preview_filename = result["preview_filename"]

    logger.info("OCR done [%s]: %d pages, %d chars", engine, page_count, len(full_text))

    return OCRResponse(
        image_id=image_id,
        full_text=full_text,
        words=all_words,
        blocks=all_blocks,
        page_count=page_count,
        preview_url=f"/uploads/{preview_filename}",
        is_pdf=is_pdf,
        original_pdf_url=f"/uploads/{image_id}{ext}" if is_pdf else None,
        engine=engine,
    )


# ── Engine helpers ──────────────────────────────────────────────────


async def _ocr_gemini(save_path: Path, is_pdf: bool, image_id: str) -> dict:
    """Gemini handles both images and PDFs natively in a single API call."""
    logger.info("Gemini OCR: %s", save_path.name)
    result = await asyncio.to_thread(run_gemini_ocr, str(save_path))

    if is_pdf:
        # Still render page-1 preview for the frontend
        page_images = await asyncio.to_thread(
            pdf_to_images, save_path, UPLOADS_DIR, image_id
        )
        page_count = max(len(page_images), 1)
        preview_filename = f"{image_id}_page_1.png"
    else:
        page_count = 1
        preview_filename = save_path.name

    return {**result, "page_count": page_count, "preview_filename": preview_filename}


async def _ocr_tesseract(save_path: Path, is_pdf: bool, image_id: str, ext: str) -> dict:
    """Tesseract processes one image at a time."""
    if is_pdf:
        logger.info("Tesseract OCR (PDF): converting pages…")
        page_images = await asyncio.to_thread(
            pdf_to_images, save_path, UPLOADS_DIR, image_id
        )
        if not page_images:
            raise HTTPException(400, "PDF has no pages")

        all_text, all_words, all_blocks = [], [], []
        for i, page_img in enumerate(page_images):
            logger.info("Tesseract page %d/%d", i + 1, len(page_images))
            r = await asyncio.to_thread(run_ocr, str(page_img))
            all_text.append(r["full_text"])
            all_words.extend(r["words"])
            all_blocks.extend(r["blocks"])

        return {
            "full_text": "\n\n".join(all_text),
            "words": all_words,
            "blocks": all_blocks,
            "page_count": len(page_images),
            "preview_filename": f"{image_id}_page_1.png",
        }

    logger.info("Tesseract OCR (image): %s", save_path.name)
    result = await asyncio.to_thread(run_ocr, str(save_path))
    return {
        **result,
        "page_count": 1,
        "preview_filename": f"{image_id}{ext}",
    }
