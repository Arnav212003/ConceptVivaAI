"""Google OAuth, cookie sessions, CSRF and guest-history migration (Google is mocked)."""
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException

import auth
from tests.test_api_flows import start_test_session
from tests.test_grading_evaluators import answer_output

CLIENT_ID = "test-client.apps.googleusercontent.com"


@pytest.fixture()
def google(override_settings, monkeypatch):
    override_settings(
        google_client_id=CLIENT_ID,
        google_client_secret="test-secret",
        oauth_redirect_uri="http://localhost:3000/api/auth/google/callback",
        cookie_secure=False,
    )
    identity = {"sub": "google-user-1", "email": "student@example.com", "name": "Student", "email_verified": True}

    async def fake_exchange(code, verifier, nonce):
        assert code == "good-code"
        assert len(verifier) >= 43  # PKCE verifier is passed through to the exchange
        claims = {**identity, "iss": "https://accounts.google.com", "aud": CLIENT_ID, "nonce": nonce}
        auth.validate_claims(claims, nonce)
        return claims

    monkeypatch.setattr(auth, "exchange_code_for_claims", fake_exchange)
    return identity


def sign_in(client):
    login = client.get("/auth/google/login?return_to=/dashboard", follow_redirects=False)
    assert login.status_code == 302
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]
    oauth_cookie = login.cookies.get(auth.OAUTH_COOKIE)
    callback = client.get(
        f"/auth/google/callback?code=good-code&state={state}",
        headers={"Cookie": f"{auth.OAUTH_COOKIE}={oauth_cookie}"},
        follow_redirects=False,
    )
    assert callback.status_code == 302, callback.text
    assert callback.headers["location"] == "/dashboard?login=success"
    # The test client keeps the Set-Cookie values in its jar, like a browser would.
    return callback.cookies[auth.CSRF_COOKIE], callback


def jar_value(client, name):
    return next(cookie.value for cookie in client.cookies.jar if cookie.name == name)


def test_login_disabled_when_google_not_configured(client):
    assert client.get("/auth/me").json() == {
        "authenticated": False, "user": None, "google_oauth_enabled": False,
    }
    assert client.get("/auth/google/login", follow_redirects=False).status_code == 503


def test_login_redirect_uses_pkce_state_and_nonce(client, google):
    response = client.get("/auth/google/login", follow_redirects=False)
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["client_id"] == [CLIENT_ID]
    assert query["state"][0] and query["nonce"][0]
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie and "samesite=lax" in set_cookie and "path=/api/auth" in set_cookie


def test_callback_rejects_state_mismatch_and_tampered_cookie(client, google):
    login = client.get("/auth/google/login", follow_redirects=False)
    oauth_cookie = login.cookies.get(auth.OAUTH_COOKIE)
    wrong_state = client.get("/auth/google/callback?code=good-code&state=attacker",
                             headers={"Cookie": f"{auth.OAUTH_COOKIE}={oauth_cookie}"}, follow_redirects=False)
    assert wrong_state.headers["location"] == "/?auth_error=state"

    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]
    tampered = client.get(f"/auth/google/callback?code=good-code&state={state}",
                          headers={"Cookie": f"{auth.OAUTH_COOKIE}={oauth_cookie[:-2]}xx"}, follow_redirects=False)
    assert tampered.headers["location"] == "/?auth_error=state"


def test_session_cookie_is_httponly_and_csrf_cookie_is_readable(client, google):
    _, callback = sign_in(client)
    cookies = callback.headers.get_list("set-cookie")
    auth_cookie = next(c for c in cookies if c.startswith(f"{auth.AUTH_COOKIE}=")).lower()
    csrf_cookie = next(c for c in cookies if c.startswith(f"{auth.CSRF_COOKIE}=")).lower()
    assert "httponly" in auth_cookie
    assert "httponly" not in csrf_cookie
    me = client.get("/auth/me").json()
    assert me["authenticated"] is True
    assert me["user"]["email"] == "student@example.com"


def test_cookie_auth_requires_csrf_on_unsafe_requests(client, google, fake_llm):
    csrf, _ = sign_in(client)
    fake_llm.responses["AnswerEvaluationOutput"] = answer_output()
    payload = {"topic": "KNN", "question": "What is KNN?", "answer": "neighbours vote", "mode": "practice",
               "save_attempt": True}

    # Reads work with the cookie alone.
    assert client.get("/dashboard-stats").status_code == 200

    assert client.post("/evaluate-answer", json=payload).status_code == 403
    assert client.post("/evaluate-answer", json=payload, headers={"X-CSRF-Token": "forged"}).status_code == 403
    cross_site = client.post("/evaluate-answer", json=payload,
                             headers={"X-CSRF-Token": csrf, "Origin": "https://evil.example"})
    assert cross_site.status_code == 403

    ok = client.post("/evaluate-answer", json=payload,
                     headers={"X-CSRF-Token": csrf, "Origin": "http://localhost:3000"})
    assert ok.status_code == 200
    assert ok.json()["saved_attempt"]["session_id"] == "usr_1"


def test_planted_csrf_cookie_is_not_accepted(client, google):
    sign_in(client)
    auth_cookie = jar_value(client, auth.AUTH_COOKIE)
    client.cookies.clear()
    client.cookies.set(auth.AUTH_COOKIE, auth_cookie)
    client.cookies.set(auth.CSRF_COOKIE, "attacker-chosen")
    response = client.post("/generate-question", json={"topic": "KNN"},
                           headers={"X-CSRF-Token": "attacker-chosen"})
    assert response.status_code == 403


def test_guest_history_migration_is_safe_and_idempotent(client, google, fake_llm):
    _, guest_headers = start_test_session(client)
    fake_llm.responses["AnswerEvaluationOutput"] = answer_output(3, 2, 2, 1)
    client.post("/evaluate-answer", headers=guest_headers, json={
        "topic": "KNN", "question": "What is KNN?", "answer": "neighbours vote",
        "mode": "practice", "save_attempt": True,
    })

    csrf, _ = sign_in(client)
    signed_in = {"X-CSRF-Token": csrf}

    # Without guest proof nothing moves.
    assert client.post("/auth/migrate-guest-history", headers=signed_in).status_code == 403

    moved = client.post("/auth/migrate-guest-history", headers={**signed_in, **guest_headers}).json()
    assert moved == {"migrated": True, "already_migrated": False, "rows_moved": 1}

    stats = client.get("/dashboard-stats").json()["ml_practice"]
    assert stats["total_attempts"] == 1 and stats["average_score"] == 8.0

    again = client.post("/auth/migrate-guest-history", headers={**signed_in, **guest_headers}).json()
    assert again["already_migrated"] is True

    # The guest token was revoked, so it cannot keep writing to the old id.
    client.cookies.clear()
    assert client.get("/dashboard-stats", headers=guest_headers).status_code == 403


def test_migration_requires_login_and_csrf(client, google):
    _, guest_headers = start_test_session(client)
    assert client.post("/auth/migrate-guest-history", headers=guest_headers).status_code == 401
    sign_in(client)
    assert client.post("/auth/migrate-guest-history", headers=guest_headers).status_code == 403


def test_logout_revokes_session(client, google):
    csrf, _ = sign_in(client)
    old_cookie = jar_value(client, auth.AUTH_COOKIE)
    assert client.post("/auth/logout", headers={"X-CSRF-Token": csrf}).json() == {"logged_out": True}

    client.cookies.clear()
    client.cookies.set(auth.AUTH_COOKIE, old_cookie)
    assert client.get("/auth/me").json()["authenticated"] is False
    # Falls back to guest auth, which requires headers.
    assert client.get("/dashboard-stats").status_code == 401


def test_expired_session_is_rejected(client, google):
    sign_in(client)
    from database import SessionLocal
    from models import AuthSession

    db = SessionLocal()
    try:
        record = db.query(AuthSession).first()
        record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()
    assert client.get("/auth/me").json()["authenticated"] is False


@pytest.mark.parametrize("value,expected", [
    ("/dsa/practice", "/dsa/practice"),
    ("//evil.com", "/dashboard"),
    ("https://evil.com", "/dashboard"),
    ("/\\evil.com", "/dashboard"),
    ("", "/dashboard"),
])
def test_return_path_blocks_open_redirects(value, expected):
    assert auth.safe_return_path(value) == expected


@pytest.mark.parametrize("override,detail", [
    ({"iss": "https://evil.example"}, "issuer"),
    ({"aud": "someone-else"}, "audience"),
    ({"nonce": "replayed"}, "nonce"),
    ({"email_verified": False}, "not verified"),
])
def test_id_token_claim_validation(override_settings, override, detail):
    override_settings(google_client_id=CLIENT_ID)
    claims = {"iss": "accounts.google.com", "aud": CLIENT_ID, "nonce": "n1", "email_verified": True, "sub": "1"}
    claims.update(override)
    with pytest.raises(HTTPException) as exc:
        auth.validate_claims(claims, "n1")
    assert detail in exc.value.detail
