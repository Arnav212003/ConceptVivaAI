import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import RevokedSession


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env.local")
load_dotenv(BASE_DIR / ".env")


SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")

if not SESSION_SECRET_KEY:
    raise RuntimeError(
        "SESSION_SECRET_KEY is missing. Add SESSION_SECRET_KEY in .env.local before running backend."
    )

SESSION_TTL_SECONDS = int(
    os.getenv("SESSION_TTL_SECONDS", str(60 * 60 * 24 * 30))
)


def _sign_message(message: str) -> str:
    return hmac.new(
        SESSION_SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def get_session_token_hash(session_id: str, session_token: str) -> str:
    raw_value = f"{session_id}.{session_token}"

    return hashlib.sha256(
        raw_value.encode("utf-8")
    ).hexdigest()


def create_session_credentials():
    session_id = "cv_" + secrets.token_urlsafe(32)
    issued_at = int(time.time())

    message = f"{session_id}.{issued_at}"
    signature = _sign_message(message)

    session_token = f"{issued_at}.{signature}"

    return {
        "session_id": session_id,
        "session_token": session_token,
        "expires_in_seconds": SESSION_TTL_SECONDS,
    }


def verify_session_token(session_id: str, session_token: str) -> bool:
    if not session_id or not session_token:
        return False

    try:
        issued_at_text, received_signature = session_token.split(".", 1)
        issued_at = int(issued_at_text)
    except Exception:
        return False

    current_time = int(time.time())

    if current_time - issued_at > SESSION_TTL_SECONDS:
        return False

    message = f"{session_id}.{issued_at}"
    expected_signature = _sign_message(message)

    return hmac.compare_digest(expected_signature, received_signature)


def is_session_revoked(db: Session, session_id: str, session_token: str) -> bool:
    token_hash = get_session_token_hash(session_id, session_token)

    revoked = db.query(RevokedSession).filter(
        RevokedSession.session_id == session_id,
        RevokedSession.token_hash == token_hash,
    ).first()

    return revoked is not None


def revoke_session_token(
    db: Session,
    session_id: str,
    session_token: str,
    reason: str = "User logout",
):
    token_hash = get_session_token_hash(session_id, session_token)

    existing = db.query(RevokedSession).filter(
        RevokedSession.session_id == session_id,
        RevokedSession.token_hash == token_hash,
    ).first()

    if existing:
        return existing

    revoked_session = RevokedSession(
        session_id=session_id,
        token_hash=token_hash,
        reason=reason,
    )

    db.add(revoked_session)
    db.commit()
    db.refresh(revoked_session)

    return revoked_session


def get_current_session_id(
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id"),
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
    db: Session = Depends(get_db),
):
    if not x_session_id or not x_session_token:
        raise HTTPException(
            status_code=401,
            detail="Missing session headers.",
        )

    is_valid = verify_session_token(
        session_id=x_session_id,
        session_token=x_session_token,
    )

    if not is_valid:
        raise HTTPException(
            status_code=403,
            detail="Invalid or expired session.",
        )

    if is_session_revoked(
        db=db,
        session_id=x_session_id,
        session_token=x_session_token,
    ):
        raise HTTPException(
            status_code=403,
            detail="Session has been logged out or revoked.",
        )

    return x_session_id