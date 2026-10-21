import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import RevokedSession


SESSION_SECRET_KEY = settings.session_secret_key
SESSION_TTL_SECONDS = settings.session_ttl_seconds


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

    # Reject expired tokens and tokens issued implausibly far in the future.
    if current_time - issued_at > SESSION_TTL_SECONDS:
        return False

    if issued_at - current_time > 300:
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
    request: Request,
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id"),
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
    db: Session = Depends(get_db),
):
    """Owner id for this request.

    A valid sign-in cookie wins (returns `usr_<id>`, CSRF-checked). Otherwise the
    guest HMAC session headers are used, exactly as before accounts existed.
    """
    from auth import resolve_cookie_owner

    owner = resolve_cookie_owner(request, db)
    if owner:
        return owner

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

EVALUATION_RECEIPT_TTL_SECONDS = settings.evaluation_receipt_ttl_seconds


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def create_evaluation_receipt(
    session_id: str,
    kind: str,
    score: float,
    verdict: str = "",
    metadata: Optional[dict] = None,
) -> str:
    """Create a signed receipt for a backend-generated score."""
    payload = {
        "sid": session_id,
        "kind": kind,
        "score": max(0.0, min(10.0, float(score))),
        "verdict": str(verdict or ""),
        "iat": int(time.time()),
        "meta": metadata or {},
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body = _b64url_encode(raw)
    signature = _sign_message(f"evaluation.{body}")
    return f"{body}.{signature}"


def verify_evaluation_receipt(
    session_id: str,
    receipt: str,
    expected_kind: Optional[str] = None,
) -> Optional[dict]:
    if not session_id or not receipt:
        return None

    try:
        body, received_signature = receipt.rsplit(".", 1)
        expected_signature = _sign_message(f"evaluation.{body}")
        if not hmac.compare_digest(expected_signature, received_signature):
            return None

        payload = json.loads(_b64url_decode(body).decode("utf-8"))
        if payload.get("sid") != session_id:
            return None
        if expected_kind and payload.get("kind") != expected_kind:
            return None

        issued_at = int(payload.get("iat", 0))
        now = int(time.time())
        if now - issued_at > EVALUATION_RECEIPT_TTL_SECONDS:
            return None
        if issued_at - now > 300:
            return None

        score = float(payload.get("score", 0))
        if score < 0 or score > 10:
            return None
        payload["score"] = score
        return payload
    except Exception:
        return None
