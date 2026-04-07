from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..services.export_service import export_pdf, export_docx, export_txt
from ..models.schemas import ExportRequest

router = APIRouter(prefix="/api", tags=["export"])

MIME_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
}


@router.post("/export")
async def export_document(req: ExportRequest):
    fmt = req.format.lower()
    filename = req.filename or "document"

    if fmt == "pdf":
        buf = export_pdf(req.text, filename)
        ext = ".pdf"
    elif fmt == "docx":
        buf = export_docx(req.text, filename)
        ext = ".docx"
    elif fmt == "txt":
        buf = export_txt(req.text, filename)
        ext = ".txt"
    else:
        raise HTTPException(400, f"Unsupported format: {fmt}. Use pdf, docx, or txt.")

    return StreamingResponse(
        buf,
        media_type=MIME_TYPES[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}{ext}"'},
    )
