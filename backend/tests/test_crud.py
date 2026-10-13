"""Tests for pure helper functions in crud.py."""

import json
from crud import _normalize_json_for_db, decode_project_challenge, _safe_limit_offset


def test_normalize_json_handles_dict():
    result = _normalize_json_for_db({"a": 1})
    assert json.loads(result) == {"a": 1}


def test_normalize_json_handles_double_encoded_string():
    # Frontend can send already-stringified JSON.
    double_encoded = json.dumps(json.dumps({"a": 1}))
    result = _normalize_json_for_db(double_encoded)
    assert json.loads(result) == {"a": 1}


def test_normalize_json_handles_invalid_string():
    result = _normalize_json_for_db("not json at all")
    assert json.loads(result) == {"raw": "not json at all"}


def test_normalize_json_handles_none():
    result = _normalize_json_for_db(None)
    assert json.loads(result) == {}


def test_decode_project_challenge_reverses_normalize():
    stored = _normalize_json_for_db({"title": "Test Challenge"})
    decoded = decode_project_challenge(stored)
    assert decoded == {"title": "Test Challenge"}


def test_decode_project_challenge_handles_none():
    assert decode_project_challenge(None) == {}


def test_safe_limit_offset_defaults_on_bad_input():
    limit, offset = _safe_limit_offset("bad", "bad")
    assert limit == 20
    assert offset == 0


def test_safe_limit_offset_caps_limit_at_100():
    limit, offset = _safe_limit_offset(500, 0)
    assert limit == 100


def test_safe_limit_offset_rejects_negative_offset():
    limit, offset = _safe_limit_offset(20, -5)
    assert offset == 0
