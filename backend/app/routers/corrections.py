from fastapi import APIRouter

from ..services.correction_service import save_correction, list_corrections
from ..models.schemas import CorrectionRequest, CorrectionResponse

router = APIRouter(prefix="/api", tags=["corrections"])


@router.post("/corrections", response_model=CorrectionResponse)
async def submit_correction(req: CorrectionRequest):
    word_corrections = [wc.model_dump() for wc in req.word_corrections]
    correction_id = save_correction(
        image_id=req.image_id,
        original_text=req.original_text,
        corrected_text=req.corrected_text,
        word_corrections=word_corrections,
    )
    return CorrectionResponse(id=correction_id, message="Correction saved")


@router.get("/corrections")
async def get_corrections():
    return list_corrections()
