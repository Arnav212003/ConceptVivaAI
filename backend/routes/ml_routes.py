from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from crud import create_ml_practice_attempt
from database import get_db
from rate_limit import enforce_rate_limit
from routes.interview_routes import ml_attempt_record
from schemas import EvaluateRequest, SaveMLPracticeAttemptRequest
from security import get_current_session_id
from serializers import serialize_ml_attempt
from services.interview_service import evaluate_semantic_answer_with_gemini

router = APIRouter(tags=["ml"])


@router.post("/save-ml-practice-attempt")
async def save_ml_practice_attempt(
    request: SaveMLPracticeAttemptRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db),
):
    """Legacy compatibility endpoint. Client score fields are ignored."""
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    evaluation_request = EvaluateRequest(
        topic=request.topic,
        display_topic=request.topic,
        level=request.level,
        question=request.question,
        answer=request.answer,
        mode="practice",
        save_attempt=False,
    )
    result = await evaluate_semantic_answer_with_gemini(evaluation_request)
    attempt = await run_in_threadpool(
        create_ml_practice_attempt, db, ml_attempt_record(session_id, evaluation_request, result)
    )
    return {
        "message": "ML attempt re-evaluated and saved by backend.",
        "evaluation_status": result["evaluation_status"],
        "attempt": serialize_ml_attempt(attempt),
    }
