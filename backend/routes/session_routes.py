from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from rate_limit import enforce_rate_limit
from security import (
    create_session_credentials,
    get_current_session_id,
    revoke_session_token,
)

router = APIRouter(tags=["session"])


@router.post("/session/start")
def start_session(request: Request):
    enforce_rate_limit(request, bucket="session_start")
    return create_session_credentials()


@router.post("/session/logout")
def logout_session(
    session_id: str = Depends(get_current_session_id),
    x_session_token: str = Header(default="", alias="X-Session-Token"),
    db: Session = Depends(get_db),
):
    if not x_session_token:
        raise HTTPException(
            status_code=401,
            detail="Missing session token.",
        )

    revoke_session_token(
        db=db,
        session_id=session_id,
        session_token=x_session_token,
        reason="User logout",
    )

    return {
        "message": "Session logged out successfully.",
        "session_id": session_id,
        "revoked": True,
    }
