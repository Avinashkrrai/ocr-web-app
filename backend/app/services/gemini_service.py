import os
import logging
from pathlib import Path

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_client: genai.Client | None = None

OCR_PROMPT = (
    "Extract ALL text from this document with high accuracy.\n\n"
    "Rules:\n"
    "- Preserve paragraph structure and reading order\n"
    "- Keep headings, lists, and table formatting\n"
    "- For tables, represent them as neatly aligned text\n"
    "- For graphs or figures, briefly describe them in [brackets]\n"
    "- For old or degraded text, use context to infer unclear characters\n"
    "- Return ONLY the extracted text — no commentary or explanation"
)


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable is not set. "
                "Get a free key at https://aistudio.google.com/apikey"
            )
        _client = genai.Client(api_key=api_key)
    return _client


def _mime_for(path: Path) -> str:
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
    }.get(path.suffix.lower(), "image/png")


def _call_gemini(file_path: Path) -> str:
    client = get_client()
    data = file_path.read_bytes()
    mime = _mime_for(file_path)
    logger.info("Gemini request: %s (%s, %.1f KB)", file_path.name, mime, len(data) / 1024)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=data, mime_type=mime),
            OCR_PROMPT,
        ],
    )
    return (response.text or "").strip()


def run_gemini_ocr(file_path: str) -> dict:
    """Run OCR via Gemini — works for both images and PDFs."""
    text = _call_gemini(Path(file_path))
    return {
        "full_text": text,
        "words": [],
        "blocks": [],
    }
