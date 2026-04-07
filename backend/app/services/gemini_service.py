import os
import json
import logging
from pathlib import Path

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_client: genai.Client | None = None

# ── Prompt library ──────────────────────────────────────────────────

PROMPTS = {
    "general": (
        "Extract ALL text from this document with high accuracy.\n\n"
        "Rules:\n"
        "- Preserve paragraph structure and reading order\n"
        "- Keep headings, lists, and table formatting\n"
        "- For tables, represent them as neatly aligned text\n"
        "- For graphs or figures, briefly describe them in [brackets]\n"
        "- For old or degraded text, use context to infer unclear characters\n"
        "- Return ONLY the extracted text — no commentary or explanation"
    ),
    "land_document": (
        "You are an expert at reading old land and property records.\n\n"
        "Extract ALL text from this document image with the highest possible accuracy.\n\n"
        "Context:\n"
        "- This is an old land/property document (deed, survey, revenue record, patta, "
        "khata, mutation register, sale deed, or similar).\n"
        "- It may be handwritten, printed, or a mix of both.\n"
        "- The paper may be yellowed, stained, torn, or faded.\n"
        "- It may contain regional language text, legal terminology, or revenue codes.\n\n"
        "Rules:\n"
        "- Read every word carefully — accuracy is critical for legal documents\n"
        "- Preserve the original layout: columns, tables, margins, headers\n"
        "- For tables (common in land records), align columns neatly\n"
        "- Transcribe stamps, seals, and annotations if readable\n"
        "- For unclear characters, use surrounding context to infer them "
        "and mark uncertain words with [?] after them\n"
        "- Preserve original numbering, survey numbers, plot numbers exactly\n"
        "- Return ONLY the extracted text — no commentary"
    ),
}

ANALYZE_PROMPT = (
    "You are an expert at analyzing old land and property documents.\n\n"
    "Analyze this document and extract structured information.\n"
    "Return a JSON object with exactly this structure:\n\n"
    "{\n"
    '  "document_type": "type of document (e.g. Sale Deed, Revenue Record, Survey Map, Patta, Mutation)",\n'
    '  "summary": "2-3 sentence summary of what this document contains",\n'
    '  "language": "primary language of the document",\n'
    '  "estimated_date": "date or approximate era of the document, or null",\n'
    '  "fields": {\n'
    '    "owner_names": ["list of owner/party names found"],\n'
    '    "survey_number": "survey or khasra number, or null",\n'
    '    "plot_number": "plot or khata number, or null",\n'
    '    "area": "land area with units, or null",\n'
    '    "location": "village, taluk, district, or address info",\n'
    '    "boundaries": {\n'
    '      "north": "north boundary description or null",\n'
    '      "south": "south boundary description or null",\n'
    '      "east": "east boundary description or null",\n'
    '      "west": "west boundary description or null"\n'
    "    },\n"
    '    "registration_number": "registration or document number, or null",\n'
    '    "consideration_amount": "sale price or value mentioned, or null",\n'
    '    "witnesses": ["list of witness names, or empty"],\n'
    '    "additional_details": "any other important details"\n'
    "  },\n"
    '  "confidence": 0.85,\n'
    '  "uncertain_sections": ["list of text portions that were hard to read"]\n'
    "}\n\n"
    "Rules:\n"
    "- Fill in every field you can find in the document\n"
    "- Use null for fields that are not present\n"
    "- confidence: your estimated overall accuracy from 0.0 to 1.0\n"
    "- uncertain_sections: quote the specific text that was difficult to read\n"
    "- Return ONLY valid JSON — no markdown fences, no commentary"
)


# ── Client ──────────────────────────────────────────────────────────

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


def _call_gemini(file_path: Path, prompt: str) -> str:
    client = get_client()
    data = file_path.read_bytes()
    mime = _mime_for(file_path)
    logger.info("Gemini request: %s (%s, %.1f KB)", file_path.name, mime, len(data) / 1024)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=data, mime_type=mime),
            prompt,
        ],
    )
    return (response.text or "").strip()


# ── Public API ──────────────────────────────────────────────────────

def run_gemini_ocr(file_path: str, doc_type: str = "general") -> dict:
    """Run OCR via Gemini — works for both images and PDFs."""
    prompt = PROMPTS.get(doc_type, PROMPTS["general"])
    text = _call_gemini(Path(file_path), prompt)
    return {
        "full_text": text,
        "words": [],
        "blocks": [],
    }


def run_gemini_analysis(file_path: str) -> dict:
    """Extract structured fields from a land/property document."""
    raw = _call_gemini(Path(file_path), ANALYZE_PROMPT)

    # Strip markdown code fences if Gemini wraps the JSON
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Gemini returned non-JSON analysis, returning raw text")
        return {
            "document_type": "Unknown",
            "summary": raw[:500],
            "language": "Unknown",
            "estimated_date": None,
            "fields": {},
            "confidence": 0.0,
            "uncertain_sections": ["Could not parse structured response"],
        }
