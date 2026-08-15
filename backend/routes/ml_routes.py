from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from crud import create_ml_practice_attempt
from database import get_db
from rate_limit import enforce_rate_limit
from schemas import EvaluateRequest, SaveMLPracticeAttemptRequest
from security import get_current_session_id
from serializers import serialize_ml_attempt
from services.interview_service import evaluate_semantic_answer_with_gemini

router = APIRouter(tags=["ml"])


@router.post("/save-ml-practice-attempt")
def save_ml_practice_attempt(
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
    result = evaluate_semantic_answer_with_gemini(evaluation_request)
    attempt = create_ml_practice_attempt(
        db,
        {
            "session_id": session_id,
            "topic": request.topic,
            "level": request.level,
            "question": request.question,
            "answer": request.answer,
            "score": result.get("score", 0),
            "verdict": result.get("verdict", "PARTIAL"),
            "feedback": result.get("feedback", ""),
            "missing_points": result.get("missing_points", ""),
            "corrected_answer": result.get("corrected_answer", ""),
            "improvement": result.get("improvement", ""),
        },
    )
    return {
        "message": "ML attempt re-evaluated and saved by backend.",
        "attempt": serialize_ml_attempt(attempt),
    }
