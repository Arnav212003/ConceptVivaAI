from fastapi import APIRouter, Depends, Request

from rate_limit import enforce_rate_limit
from schemas import TranslateRequest
from security import get_current_session_id
from services.translate_service import translate_to_hindi_with_gemini

router = APIRouter(tags=["translate"])


@router.post("/translate-to-hindi")
async def translate_to_hindi(
    request: TranslateRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
):
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    return await translate_to_hindi_with_gemini(request.text)
