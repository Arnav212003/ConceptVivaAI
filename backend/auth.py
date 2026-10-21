"""Google OAuth sign-in with HttpOnly cookie sessions and CSRF protection.

Flow (all browser traffic goes through the Next.js proxy, so cookies are first-party):
1. GET  /auth/google/login     -> state + PKCE verifier + nonce in a short-lived signed
                                 HttpOnly cookie, then 302 to Google.
2. GET  /auth/google/callback  -> check state, exchange the code (with PKCE) server to
                                 server, verify the ID token (audience, issuer, expiry,
                                 nonce, email_verified), create a session, set cookies.
3. POST /auth/migrate-guest-history -> optional, explicit merge of the browser's guest
                                 history into the account (proves guest token ownership).

Cookies
- cv_auth  : random session token, HttpOnly, SameSite=Lax, Secure in production. The
             database stores only its SHA-256 hash, so a DB leak does not leak sessions.
- cv_csrf  : readable by JS; must be echoed in X-CSRF-Token on unsafe requests.
             Its value is HMAC(secret, session id), so an attacker who can plant a
             cookie still cannot forge a value the server accepts (double submit + binding).
Unsafe cookie-authenticated requests must also carry an allowed Origin, when present.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from config import settings
from models import AuthSession, User

AUTH_COOKIE = "cv_auth"
CSRF_COOKIE = "cv_csrf"
OAUTH_COOKIE = "cv_oauth"
OAUTH_COOKIE_TTL = 600
CSRF_HEADER = "x-csrf-token"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


# ------------------------------------------------------------------ helpers


def _sign(message: str) -> str:
    return hmac.new(settings.session_secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def safe_return_path(value: str | None) -> str:
    """Only same-site absolute paths; blocks open redirects like //evil.com or /\\evil."""
    if not value or not value.startswith("/") or value.startswith("//") or "\\" in value:
        return "/dashboard"
    return value[:300]


def cookie_options(max_age: int, *, http_only: bool = True, path: str = "/") -> dict:
    return {
        "max_age": max_age,
        "httponly": http_only,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": path,
    }


# ------------------------------------------------------------------ OAuth state


def build_login_redirect(return_to: str | None) -> tuple[str, str]:
    """Return (google_url, signed_state_cookie_value)."""
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(48)
    challenge = _b64(hashlib.sha256(verifier.encode()).digest())

    payload = _b64(json.dumps({
        "state": state, "nonce": nonce, "verifier": verifier,
        "return_to": safe_return_path(return_to), "exp": int(time.time()) + OAUTH_COOKIE_TTL,
    }).encode())
    cookie_value = f"{payload}.{_sign('oauth.' + payload)}"

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.oauth_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}", cookie_value


def read_oauth_cookie(cookie_value: str | None) -> dict | None:
    if not cookie_value or "." not in cookie_value:
        return None
    payload, signature = cookie_value.rsplit(".", 1)
    if not hmac.compare_digest(_sign("oauth." + payload), signature):
        return None
    try:
        data = json.loads(_unb64(payload))
    except ValueError:
        return None
    if int(data.get("exp", 0)) < time.time():
        return None
    return data


async def exchange_code_for_claims(code: str, verifier: str, nonce: str) -> dict:
    """Server-to-server code exchange, then full ID-token verification."""
    import httpx
    from fastapi.concurrency import run_in_threadpool

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.oauth_redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        })
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Google sign-in failed.")
    id_token_value = response.json().get("id_token")
    if not id_token_value:
        raise HTTPException(status_code=401, detail="Google sign-in failed.")
    claims = await run_in_threadpool(verify_google_id_token, id_token_value)
    validate_claims(claims, nonce)
    return claims


def verify_google_id_token(token: str) -> dict:
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    # Verifies signature against Google's published keys, audience and expiry.
    return id_token.verify_oauth2_token(token, google_requests.Request(), settings.google_client_id)


def validate_claims(claims: dict, expected_nonce: str) -> None:
    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise HTTPException(status_code=401, detail="Invalid token issuer.")
    if claims.get("aud") != settings.google_client_id:
        raise HTTPException(status_code=401, detail="Invalid token audience.")
    if not hmac.compare_digest(str(claims.get("nonce", "")), expected_nonce):
        raise HTTPException(status_code=401, detail="Invalid sign-in nonce.")
    if not claims.get("email_verified"):
        raise HTTPException(status_code=403, detail="Google account email is not verified.")
    if not claims.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid token subject.")


# ------------------------------------------------------------------ users and sessions


def upsert_user(db: Session, claims: dict) -> User:
    user = db.query(User).filter(User.google_sub == claims["sub"]).first()
    if user is None:
        user = User(google_sub=claims["sub"])
        db.add(user)
    user.email = str(claims.get("email", ""))[:320]
    user.name = str(claims.get("name", ""))[:255]
    user.picture_url = str(claims.get("picture", ""))[:1000]
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


def create_auth_session(db: Session, user: User) -> tuple[str, AuthSession]:
    token = secrets.token_urlsafe(32)
    record = AuthSession(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.auth_session_ttl_seconds),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return token, record


def csrf_token_for(record: AuthSession) -> str:
    return _sign(f"csrf.{record.id}.{record.token_hash}")


def load_auth_session(db: Session, token: str | None) -> tuple[AuthSession, User] | None:
    if not token or len(token) > 200:
        return None
    record = db.query(AuthSession).filter(AuthSession.token_hash == hash_token(token)).first()
    if record is None or record.revoked_at is not None:
        return None
    if _utc(record.expires_at) <= datetime.now(timezone.utc):
        return None
    user = db.get(User, record.user_id)
    if user is None:
        return None
    return record, user


def revoke_auth_session(db: Session, record: AuthSession) -> None:
    record.revoked_at = datetime.now(timezone.utc)
    db.commit()


def enforce_csrf(request: Request, record: AuthSession) -> None:
    """Origin check + HMAC-bound double-submit token for unsafe cookie requests."""
    if request.method not in UNSAFE_METHODS:
        return
    origin = request.headers.get("origin")
    if origin and origin not in settings.cors_origins:
        raise HTTPException(status_code=403, detail="Cross-site request blocked.")
    header = request.headers.get(CSRF_HEADER, "")
    cookie = request.cookies.get(CSRF_COOKIE, "")
    expected = csrf_token_for(record)
    if not header or not hmac.compare_digest(header, cookie) or not hmac.compare_digest(header, expected):
        raise HTTPException(status_code=403, detail="Missing or invalid CSRF token.")


def resolve_cookie_owner(request: Request, db: Session) -> str | None:
    """Owner id for a valid auth cookie (CSRF-checked), or None to fall back to guest auth."""
    loaded = load_auth_session(db, request.cookies.get(AUTH_COOKIE))
    if loaded is None:
        return None
    record, user = loaded
    enforce_csrf(request, record)
    request.state.user = user
    return user.owner_id
