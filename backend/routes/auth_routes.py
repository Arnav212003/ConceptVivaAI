import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import auth
from config import settings
from database import get_db
from models import (
    DSAAttempt,
    GuestHistoryMigration,
    InterviewReport,
    MLPracticeAttempt,
    ProjectAttempt,
    ProjectChallenge,
)
from observability import get_logger, log_event
from rate_limit import enforce_rate_limit
from security import is_session_revoked, revoke_session_token, verify_session_token

router = APIRouter(tags=["auth"], prefix="/auth")
logger = get_logger("auth")

HISTORY_TABLES = (MLPracticeAttempt, DSAAttempt, ProjectAttempt, InterviewReport, ProjectChallenge)


def _public_user(user):
    return {"name": user.name, "email": user.email, "picture_url": user.picture_url}


def _require_login(request: Request, db: Session):
    loaded = auth.load_auth_session(db, request.cookies.get(auth.AUTH_COOKIE))
    if loaded is None:
        raise HTTPException(status_code=401, detail="Sign in first.")
    record, user = loaded
    auth.enforce_csrf(request, record)
    return record, user


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    loaded = auth.load_auth_session(db, request.cookies.get(auth.AUTH_COOKIE))
    return {
        "authenticated": loaded is not None,
        "user": _public_user(loaded[1]) if loaded else None,
        "google_oauth_enabled": settings.google_oauth_configured,
    }


@router.get("/google/login")
def google_login(request: Request, return_to: str = "/dashboard"):
    if not settings.google_oauth_configured:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured on this server.")
    enforce_rate_limit(request, bucket="session_start")
    url, cookie_value = auth.build_login_redirect(return_to)
    response = RedirectResponse(url, status_code=302)
    response.set_cookie(auth.OAUTH_COOKIE, cookie_value,
                        **auth.cookie_options(auth.OAUTH_COOKIE_TTL, path="/api/auth"))
    return response


def _fail(reason: str) -> RedirectResponse:
    response = RedirectResponse(f"/?auth_error={reason}", status_code=302)
    response.delete_cookie(auth.OAUTH_COOKIE, path="/api/auth")
    return response


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    db: Session = Depends(get_db),
):
    if not settings.google_oauth_configured:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured on this server.")
    enforce_rate_limit(request, bucket="session_start")
    if error or not code:
        return _fail("cancelled")

    stored = auth.read_oauth_cookie(request.cookies.get(auth.OAUTH_COOKIE))
    if stored is None or not state or not hmac.compare_digest(stored["state"], state):
        log_event(logger, "oauth_state_mismatch", level=30)
        return _fail("state")

    try:
        claims = await auth.exchange_code_for_claims(code, stored["verifier"], stored["nonce"])
    except HTTPException:
        return _fail("verification")
    except Exception:
        log_event(logger, "oauth_exchange_error", level=40)
        return _fail("verification")

    user = auth.upsert_user(db, claims)
    token, record = auth.create_auth_session(db, user)
    log_event(logger, "login", user_id=user.id)

    separator = "&" if "?" in stored["return_to"] else "?"
    response = RedirectResponse(f"{stored['return_to']}{separator}login=success", status_code=302)
    ttl = settings.auth_session_ttl_seconds
    response.set_cookie(auth.AUTH_COOKIE, token, **auth.cookie_options(ttl))
    response.set_cookie(auth.CSRF_COOKIE, auth.csrf_token_for(record), **auth.cookie_options(ttl, http_only=False))
    response.delete_cookie(auth.OAUTH_COOKIE, path="/api/auth")
    return response


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    record, user = _require_login(request, db)
    auth.revoke_auth_session(db, record)
    log_event(logger, "logout", user_id=user.id)
    response = JSONResponse({"logged_out": True})
    response.delete_cookie(auth.AUTH_COOKIE, path="/")
    response.delete_cookie(auth.CSRF_COOKIE, path="/")
    return response


@router.post("/migrate-guest-history")
def migrate_guest_history(
    request: Request,
    x_session_id: str = Header(default="", alias="X-Session-Id"),
    x_session_token: str = Header(default="", alias="X-Session-Token"),
    db: Session = Depends(get_db),
):
    """Move this browser's guest history into the signed-in account.

    Safety: the caller must hold a valid, unrevoked guest token (proving the history
    is theirs) and a CSRF-checked login cookie. All tables move in one transaction,
    each guest session can be migrated once, and the guest token is revoked after.
    """
    _, user = _require_login(request, db)
    if not x_session_id or not verify_session_token(x_session_id, x_session_token):
        raise HTTPException(status_code=403, detail="Valid guest session headers are required.")

    existing = db.query(GuestHistoryMigration).filter(
        GuestHistoryMigration.guest_session_id == x_session_id
    ).first()
    if existing:
        if existing.user_id != user.id:
            raise HTTPException(status_code=409, detail="This guest history belongs to another account.")
        return {"migrated": False, "already_migrated": True, "rows_moved": existing.rows_moved}

    if is_session_revoked(db, x_session_id, x_session_token):
        raise HTTPException(status_code=403, detail="Guest session has been revoked.")

    moved = 0
    try:
        for model in HISTORY_TABLES:
            moved += db.query(model).filter(model.session_id == x_session_id).update(
                {model.session_id: user.owner_id}, synchronize_session=False
            )
        db.add(GuestHistoryMigration(guest_session_id=x_session_id, user_id=user.id, rows_moved=moved))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This guest history was already migrated.")

    revoke_session_token(db, x_session_id, x_session_token, reason="Merged into account")
    log_event(logger, "guest_history_migrated", user_id=user.id, rows=moved)
    return {"migrated": True, "already_migrated": False, "rows_moved": moved}
