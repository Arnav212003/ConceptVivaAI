from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from crud import create_interview_report, create_ml_practice_attempt
from database import get_db
from rate_limit import enforce_rate_limit
from schemas import EvaluateRequest, QuestionRequest, SaveInterviewReportRequest
from security import (
    create_evaluation_receipt,
    get_current_session_id,
    verify_evaluation_receipt,
)
from serializers import serialize_interview_report, serialize_ml_attempt
from services.interview_service import (
    evaluate_semantic_answer_with_gemini,
    generate_interview_question,
    interview_summary,
)

router = APIRouter(tags=["interview"])


@router.post("/generate-question")
def generate_question(
    request: QuestionRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
):
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    return {"question": generate_interview_question(request.topic, request.level)}


@router.post("/evaluate-answer")
def evaluate_answer(
    request: EvaluateRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    result = evaluate_semantic_answer_with_gemini(request)

    mode = request.mode.lower().strip()
    receipt_kind = "ml_practice" if mode == "practice" else "interview_round"
    result["evaluation_receipt"] = create_evaluation_receipt(
        session_id=session_id,
        kind=receipt_kind,
        score=result.get("score", 0),
        verdict=result.get("verdict", "PARTIAL"),
        metadata={
            "topic": (request.display_topic or request.topic)[:300],
        },
    )

    if request.save_attempt and mode == "practice":
        attempt = create_ml_practice_attempt(
            db,
            {
                "session_id": session_id,
                "topic": request.display_topic or request.topic[:255],
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
        result["saved_attempt"] = serialize_ml_attempt(attempt)

    return result


@router.post("/save-interview-report")
def save_interview_report(
    request: SaveInterviewReportRequest,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db),
):
    # Only backend-signed round scores are used for the final average.
    valid_receipts = []
    seen = set()
    for receipt in request.evaluation_receipts:
        if not receipt or receipt in seen:
            continue
        seen.add(receipt)
        payload = verify_evaluation_receipt(
            session_id=session_id,
            receipt=receipt,
            expected_kind="interview_round",
        )
        if payload:
            valid_receipts.append(payload)

    if not valid_receipts:
        raise HTTPException(
            status_code=400,
            detail="No valid interview evaluation receipts were provided.",
        )

    scores = [float(item["score"]) for item in valid_receipts]
    average_score = round(sum(scores) / len(scores), 1)
    strong_points, weak_points, recommendation = interview_summary(average_score)

    report = create_interview_report(
        db,
        {
            "session_id": session_id,
            "topic": request.topic,
            "level": request.level,
            "rounds": len(scores),
            "average_score": average_score,
            "strong_points": strong_points,
            "weak_points": weak_points,
            "recommendation": recommendation,
        },
    )

    return {
        "message": "Interview report verified and saved successfully.",
        "report": serialize_interview_report(report),
    }
