from fastapi import APIRouter, Depends

from schemas import TranslateRequest
from security import get_current_session_id
from services.translate_service import translate_to_hindi_with_gemini

router = APIRouter(tags=["translate"])


@router.post("/translate-to-hindi")
def translate_to_hindi(
    request: TranslateRequest,
    session_id: str = Depends(get_current_session_id),
):
    translated = translate_to_hindi_with_gemini(request.text)
    return {"translated_text": translated}
