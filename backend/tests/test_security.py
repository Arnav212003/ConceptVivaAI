"""
Tests for the session token signing/verification logic in security.py.
Doesn't touch the database - just the HMAC signing itself.
"""

from security import create_session_credentials, verify_session_token


def test_valid_session_token_verifies():
    creds = create_session_credentials()
    assert verify_session_token(creds["session_id"], creds["session_token"]) is True


def test_tampered_token_fails_verification():
    creds = create_session_credentials()
    tampered_token = creds["session_token"][:-1] + (
        "0" if creds["session_token"][-1] != "0" else "1"
    )
    assert verify_session_token(creds["session_id"], tampered_token) is False


def test_wrong_session_id_fails_verification():
    creds = create_session_credentials()
    assert verify_session_token("cv_someone_elses_id", creds["session_token"]) is False


def test_missing_token_fails_verification():
    assert verify_session_token("cv_some_id", "") is False


def test_missing_session_id_fails_verification():
    creds = create_session_credentials()
    assert verify_session_token("", creds["session_token"]) is False


def test_malformed_token_fails_verification():
    assert verify_session_token("cv_some_id", "not-a-valid-token-format") is False
