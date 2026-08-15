from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from crud import get_dashboard_stats, get_user_history
from database import get_db
from security import get_current_session_id
from serializers import (
    serialize_dsa_attempt,
    serialize_interview_report,
    serialize_ml_attempt,
    serialize_project_attempt,
)

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard-stats")
def dashboard_stats(
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db)
):
    return get_dashboard_stats(db, session_id)


@router.get("/history")
def history(
    limit: int = 20,
    offset: int = 0,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db)
):
    history_data = get_user_history(db, session_id, limit=limit, offset=offset)

    return {
        "session_id": session_id,
        "pagination": history_data.get(
            "pagination",
            {
                "limit": limit,
                "offset": offset,
            }
        ),
        "ml_practice": [
            serialize_ml_attempt(item)
            for item in history_data["ml_practice"]
        ],
        "dsa_practice": [
            serialize_dsa_attempt(item)
            for item in history_data["dsa_practice"]
        ],
        "project_challenge": [
            serialize_project_attempt(item)
            for item in history_data["project_challenge"]
        ],
        "voice_interview": [
            serialize_interview_report(item)
            for item in history_data["voice_interview"]
        ],
    }
