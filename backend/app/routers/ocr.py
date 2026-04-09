import os
import uuid
import shutil
import asyncio
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Query, HTTPException

import fitz  # PyMuPDF

from ..services.ocr_service import run_ocr
from ..services.gemini_service import run_gemini_ocr, run_gemini_analysis, ask_about_document
from ..services.enhance_service import enhance_document
from ..models.schemas import OCRResponse, AnalyzeRequest, AnalyzeResponse, AskRequest, AskResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ocr"])

UPLOADS_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/tiff", "image/bmp", "image/webp"}
ALLOWED_PDF_TYPES = {"application/pdf"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_PDF_TYPES

DOC_TYPES = {"general", "land_document"}


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
    """Return available OCR engines and document types."""
    engines = [{"id": "tesseract", "name": "Tesseract OCR"}]
    if os.environ.get("GEMINI_API_KEY"):
        engines.insert(0, {"id": "gemini", "name": "Gemini 2.5 Flash"})
    doc_types = [
        {"id": "general", "name": "General Document"},
        {"id": "land_document", "name": "Land / Property Record"},
    ]
    return {
        "engines": engines,
        "default": engines[0]["id"],
        "doc_types": doc_types,
    }


@router.post("/ocr", response_model=OCRResponse)
async def perform_ocr(
    file: UploadFile = File(...),
    engine: str = Query("auto"),
    doc_type: str = Query("general"),
    enhance: bool = Query(False),
):
    # ── resolve engine ──────────────────────────────────────────────
    if engine == "auto":
        engine = "gemini" if os.environ.get("GEMINI_API_KEY") else "tesseract"
    if engine not in ("gemini", "tesseract"):
        raise HTTPException(400, f"Unknown engine: {engine}")
    if doc_type not in DOC_TYPES:
        doc_type = "general"

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

    # ── optional image enhancement ──────────────────────────────────
    ocr_path = save_path
    if enhance and not is_pdf:
        try:
            enhanced = await asyncio.to_thread(enhance_document, str(save_path))
            ocr_path = Path(enhanced)
            logger.info("Using enhanced image: %s", ocr_path.name)
        except Exception:
            logger.warning("Enhancement failed, using original", exc_info=True)

    # ── run OCR ─────────────────────────────────────────────────────
    try:
        if engine == "gemini":
            result = await _ocr_gemini(ocr_path, is_pdf, image_id, doc_type, save_path)
        else:
            result = await _ocr_tesseract(
                ocr_path if not is_pdf else save_path,
                is_pdf, image_id, ext, enhance,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("OCR failed (engine=%s)", engine)
        raise HTTPException(500, f"OCR processing failed: {e}")

    logger.info("OCR done [%s/%s]: %d pages, %d chars",
                engine, doc_type, result["page_count"], len(result["full_text"]))

    return OCRResponse(
        image_id=image_id,
        full_text=result["full_text"],
        words=result["words"],
        blocks=result["blocks"],
        page_count=result["page_count"],
        preview_url=f"/uploads/{result['preview_filename']}",
        is_pdf=is_pdf,
        original_pdf_url=f"/uploads/{image_id}{ext}" if is_pdf else None,
        engine=engine,
        doc_type=doc_type,
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_document(req: AnalyzeRequest):
    """Run structured analysis on an already-uploaded document."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(400, "Document analysis requires Gemini — set GEMINI_API_KEY")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    candidates = list(UPLOADS_DIR.glob(f"{req.image_id}.*"))
    if not candidates:
        raise HTTPException(404, f"Upload {req.image_id} not found")

    file_path = candidates[0]

    try:
        logger.info("Analyzing document: %s", file_path.name)
        result = await asyncio.to_thread(run_gemini_analysis, str(file_path))
    except Exception as e:
        logger.exception("Analysis failed")
        raise HTTPException(500, f"Document analysis failed: {e}")

    return AnalyzeResponse(
        image_id=req.image_id,
        document_type=result.get("document_type", "Unknown"),
        summary=result.get("summary", ""),
        language=result.get("language", "Unknown"),
        estimated_date=result.get("estimated_date"),
        fields=result.get("fields", {}),
        confidence=result.get("confidence", 0.0),
        uncertain_sections=result.get("uncertain_sections", []),
    )


@router.post("/ask", response_model=AskResponse)
async def ask_document(req: AskRequest):
    """Ask a free-form question about an uploaded document."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(400, "Document Q&A requires Gemini — set GEMINI_API_KEY")
    if not req.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    candidates = list(UPLOADS_DIR.glob(f"{req.image_id}.*"))
    if not candidates:
        raise HTTPException(404, f"Upload {req.image_id} not found")

    file_path = candidates[0]

    try:
        logger.info("Q&A: %s — %s", file_path.name, req.question[:80])
        answer = await asyncio.to_thread(ask_about_document, str(file_path), req.question)
    except Exception as e:
        logger.exception("Q&A failed")
        raise HTTPException(500, f"Failed to answer question: {e}")

    return AskResponse(image_id=req.image_id, question=req.question, answer=answer)


# ── Engine helpers ──────────────────────────────────────────────────


async def _ocr_gemini(
    ocr_path: Path, is_pdf: bool, image_id: str, doc_type: str, original_path: Path,
) -> dict:
    """Gemini handles both images and PDFs natively in a single API call."""
    # For PDFs, always send the original (not enhanced) since Gemini reads PDFs natively
    send_path = original_path if is_pdf else ocr_path
    logger.info("Gemini OCR [%s]: %s", doc_type, send_path.name)
    result = await asyncio.to_thread(run_gemini_ocr, str(send_path), doc_type)

    if is_pdf:
        page_images = await asyncio.to_thread(
            pdf_to_images, original_path, UPLOADS_DIR, image_id
        )
        page_count = max(len(page_images), 1)
        preview_filename = f"{image_id}_page_1.png"
    else:
        page_count = 1
        preview_filename = ocr_path.name

    return {**result, "page_count": page_count, "preview_filename": preview_filename}


async def _ocr_tesseract(
    save_path: Path, is_pdf: bool, image_id: str, ext: str, enhance: bool,
) -> dict:
    """Tesseract processes one image at a time."""
    if is_pdf:
        logger.info("Tesseract OCR (PDF): converting pages…")
        page_images = await asyncio.to_thread(
            pdf_to_images, save_path, UPLOADS_DIR, image_id
        )
        if not page_images:
            raise HTTPException(400, "PDF has no pages")

        # Optionally enhance each page image for Tesseract
        if enhance:
            enhanced_images = []
            for img_path in page_images:
                try:
                    enh = await asyncio.to_thread(enhance_document, str(img_path))
                    enhanced_images.append(Path(enh))
                except Exception:
                    enhanced_images.append(img_path)
            page_images = enhanced_images

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
        "preview_filename": save_path.name,
    }
