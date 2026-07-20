"""
Tests for the small pure-logic helper functions in crud.py.

These don't touch the database - just the JSON normalization and
pagination logic, which is where the actual bugs tend to hide
(double-encoded JSON from the frontend, bad limit/offset query params).
"""

import json
import sys
import os

# so this can be run as `pytest tests/test_crud.py` from the backend folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crud import _normalize_json_for_db, decode_project_challenge, _safe_limit_offset


def test_normalize_json_handles_dict():
    result = _normalize_json_for_db({"a": 1})
    assert json.loads(result) == {"a": 1}


def test_normalize_json_handles_double_encoded_string():
    # this is the case that caused corrupted rows in the DB before the fix -
    # the frontend can send a JSON string that was already stringified once
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
