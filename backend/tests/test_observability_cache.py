"""Metrics endpoint, log redaction, and safe caching."""
import asyncio
import json
import logging

from observability import JsonFormatter, redact
from services.translate_service import translate_to_hindi_with_gemini


def test_metrics_endpoint_exposes_prometheus_text(client):
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "conceptviva_http_requests_total" in response.text
    assert 'route="/health"' in response.text


def test_metrics_token_is_enforced(client, override_settings):
    override_settings(metrics_token="s3cret")
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer s3cret"}).status_code == 200


def test_unknown_paths_do_not_create_new_metric_labels(client):
    client.get("/definitely-not-a-route-123")
    assert 'route="/definitely-not-a-route-123"' not in client.get("/metrics").text


def test_secrets_are_redacted_from_log_lines():
    assert "abc123" not in redact("calling with api_key=abc123 and token: xyz")
    record = logging.LogRecord("conceptviva.test", logging.INFO, __file__, 1, "Authorization: Bearer abc", None, None)
    record.fields = {"note": "password=hunter2"}
    line = json.loads(JsonFormatter().format(record))
    assert "hunter2" not in line["note"]
    assert "abc" not in line["msg"].replace("[REDACTED]", "")


def test_translation_is_cached_after_first_success(fake_llm):
    fake_llm.responses["text"] = "हैश मैप का उपयोग करें"
    first = asyncio.run(translate_to_hindi_with_gemini("Use a hash map."))
    second = asyncio.run(translate_to_hindi_with_gemini("Use a hash map."))
    assert first["cached"] is False and second["cached"] is True
    assert second["translated_text"] == "हैश मैप का उपयोग करें"
    assert len(fake_llm.calls) == 1


def test_failed_translation_is_not_cached(fake_llm):
    from services.llm import TransientLLMError

    fake_llm.responses["text"] = TransientLLMError("server_error_503")
    assert asyncio.run(translate_to_hindi_with_gemini("Stack"))["translated"] is False
    fake_llm.responses["text"] = "स्टैक"
    assert asyncio.run(translate_to_hindi_with_gemini("Stack"))["translated_text"] == "स्टैक"


def test_bank_problem_statement_cached_in_redis(fake_llm, fake_redis):
    from services.dsa_bank import get_dsa_question_by_title
    from services.dsa_service import generate_dsa_problem_json_from_gemini

    fake_llm.responses["DSAProblemOutput"] = {
        "title": "Two Sum", "description": "Find two indices.",
        "examples": [{"input": "nums=[2,7]", "output": "[0,1]", "explanation": "2+7"}],
        "constraints": ["2 <= n"], "follow_up": "", "starter_code": "ignored for bank questions",
    }
    question = get_dsa_question_by_title("Two Sum")
    first = asyncio.run(generate_dsa_problem_json_from_gemini(question))
    second = asyncio.run(generate_dsa_problem_json_from_gemini(question))
    assert first["generated_by"] == "ai" and second["generated_by"] == "cache"
    assert second["starter_code"] == question["starter_code"]  # bank signature enforced
    assert len(fake_llm.calls) == 1
    # Keys are hashed: no question text or user data in key names.
    assert all(key.startswith("cv:cache:dsa_problem:") for key in fake_redis.keys("cv:cache:*"))
