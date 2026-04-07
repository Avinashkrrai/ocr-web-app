from pydantic import BaseModel
from typing import Optional


class BBox(BaseModel):
    x: int
    y: int
    w: int
    h: int


class WordResult(BaseModel):
    text: str
    confidence: float
    bbox: BBox


class BlockResult(BaseModel):
    text: str
    bbox: BBox


class OCRResponse(BaseModel):
    image_id: str
    full_text: str
    words: list[WordResult]
    blocks: list[BlockResult]
    page_count: int = 1
    preview_url: Optional[str] = None
    is_pdf: bool = False
    original_pdf_url: Optional[str] = None


class ExportRequest(BaseModel):
    text: str
    format: str  # "pdf", "docx", "txt"
    filename: Optional[str] = "document"


class WordCorrection(BaseModel):
    bbox: BBox
    original: str
    corrected: str


class CorrectionRequest(BaseModel):
    image_id: str
    original_text: str
    corrected_text: str
    word_corrections: list[WordCorrection]


class CorrectionResponse(BaseModel):
    id: str
    message: str
