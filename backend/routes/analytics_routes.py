import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import analytics
from config import settings
from database import get_db
from rate_limit import enforce_rate_limit
from security import get_current_session_id

router = APIRouter(tags=["analytics"])


class AnalyticsEvent(BaseModel):
    event: str = Field(min_length=1, max_length=50)
    dimension: str = Field(default="", max_length=80)


@router.post("/analytics/event", status_code=202)
async def track_event(payload: AnalyticsEvent, request: Request, db: Session = Depends(get_db)):
    """Anonymous by design: no session headers or cookies are read or stored."""
    enforce_rate_limit(request, bucket="general")
    if not analytics.tracking_allowed(request.headers):
        return {"recorded": False, "reason": "do_not_track"}
    recorded = await run_in_threadpool(analytics.record_event, db, payload.event, payload.dimension)
    return {"recorded": recorded}


@router.get("/analytics/summary")
def analytics_summary(days: int = 30, authorization: str = Header(default=""), db: Session = Depends(get_db)):
    if not settings.analytics_admin_token:
        raise HTTPException(status_code=404, detail="Not found")
    expected = f"Bearer {settings.analytics_admin_token}"
    if not hmac.compare_digest(authorization.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Admin token required.")
    return analytics.summary(db, days)


@router.get("/progress")
def my_progress(
    request: Request,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, bucket="general", session_id=session_id)
    return analytics.progress_for_owner(db, session_id)
