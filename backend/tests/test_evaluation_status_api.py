"""End-to-end checks that AI outages never become fake scores."""
from tests.test_api_flows import start_test_session
from tests.test_grading_evaluators import answer_output


def evaluate_payload(**overrides):
    payload = {
        "topic": "KNN",
        "level": "Easy",
        "question": "What is KNN?",
        "answer": "KNN classifies by majority vote of the k nearest neighbours.",
        "mode": "practice",
        "display_topic": "KNN",
        "save_attempt": True,
    }
    payload.update(overrides)
    return payload


def test_unavailable_evaluation_is_saved_without_score_and_excluded_from_average(client, fake_llm):
    _, headers = start_test_session(client)

    # 1) A real evaluation: 8/10.
    fake_llm.responses["AnswerEvaluationOutput"] = answer_output(3, 2, 2, 1)
    ok = client.post("/evaluate-answer", headers=headers, json=evaluate_payload()).json()
    assert ok["evaluation_status"] == "completed"
    assert ok["score"] == 8.0
    assert ok["evaluation_receipt"]

    # 2) Gemini outage: must not produce a score or a receipt.
    from services.llm import TransientLLMError

    fake_llm.responses["AnswerEvaluationOutput"] = TransientLLMError("server_error_503")
    down = client.post("/evaluate-answer", headers=headers, json=evaluate_payload()).json()
    assert down["evaluation_status"] == "unavailable"
    assert down["score"] is None
    assert down["evaluation_receipt"] == ""
    assert down["saved_attempt"]["evaluation_status"] == "unavailable"
    assert down["saved_attempt"]["score"] is None

    stats = client.get("/dashboard-stats", headers=headers).json()["ml_practice"]
    assert stats["total_attempts"] == 2
    assert stats["scored_attempts"] == 1
    assert stats["unavailable_attempts"] == 1
    # The outage does not drag the average down (old behaviour stored 5.0).
    assert stats["average_score"] == 8.0


def test_interview_report_rejects_rounds_without_real_scores(client):
    _, headers = start_test_session(client)
    # No LLM configured -> every round is unavailable -> no receipts.
    round_result = client.post(
        "/evaluate-answer", headers=headers, json=evaluate_payload(mode="interview", save_attempt=False)
    ).json()
    assert round_result["evaluation_status"] == "unavailable"

    report = client.post(
        "/save-interview-report",
        headers=headers,
        json={"topic": "KNN", "level": "Easy", "evaluation_receipts": [round_result["evaluation_receipt"]]},
    )
    assert report.status_code == 400


def test_auto_topic_is_chosen_server_side(client):
    _, headers = start_test_session(client)
    response = client.post(
        "/generate-question", headers=headers, json={"auto_topic": True, "track": "ml", "level": "Easy"}
    )
    assert response.status_code == 200
    data = response.json()
    from services.interview_service import AUTO_TOPIC_POOLS

    assert data["topic"] in AUTO_TOPIC_POOLS["ml"]
    assert data["source"] == "fallback"  # no LLM configured in tests
    assert data["question"]


def test_topic_required_without_auto_topic(client):
    _, headers = start_test_session(client)
    response = client.post("/generate-question", headers=headers, json={"topic": "  ", "level": "Easy"})
    assert response.status_code == 422


def test_dsa_custom_evaluation_unavailable_is_not_scored(client):
    _, headers = start_test_session(client)
    response = client.post(
        "/evaluate-dsa-solution",
        headers=headers,
        json={
            "topic": "Tries",
            "difficulty": "Medium",
            "problem": "Problem: Implement a trie",
            "solution": "class Solution:\n    def insert(self, word):\n        pass",
            "save_attempt": True,
        },
    ).json()

    assert response["evaluation_status"] == "unavailable"
    assert response["score"] is None
    assert response["status"] == "Unavailable"
    assert response["tier"] == "ai_generated"
    assert response["evaluation_receipt"] == ""

    stats = client.get("/dashboard-stats", headers=headers).json()["dsa_practice"]
    assert stats["total_attempts"] == 1
    assert stats["scored_attempts"] == 0
    assert stats["average_score"] == 0


def test_project_outage_keeps_challenge_active_for_resubmission(client):
    _, headers = start_test_session(client)
    challenge = client.post(
        "/generate-project-challenge",
        headers=headers,
        json={"domain": "Machine Learning", "topic": "KNN", "difficulty": "Beginner"},
    ).json()
    assert challenge["challenge"]["generated_by"] == "fallback"

    submission = {
        "challenge_id": challenge["challenge_id"],
        "files": [{"path": "main.py", "content": "print('knn')"}],
    }
    first = client.post("/evaluate-project-submission", headers=headers, json=submission).json()
    assert first["evaluation_status"] == "unavailable"
    assert first["score"] is None
    assert first["evaluation_receipt"] == ""

    # The challenge was not consumed, so the student can retry.
    second = client.post("/evaluate-project-submission", headers=headers, json=submission)
    assert second.status_code == 200

    stats = client.get("/dashboard-stats", headers=headers).json()["project_challenge"]
    assert stats["active_challenges"] == 1
    assert stats["scored_attempts"] == 0


def test_translate_requires_bounded_text(client):
    _, headers = start_test_session(client)
    too_long = client.post("/translate-to-hindi", headers=headers, json={"text": "a" * 8001})
    assert too_long.status_code == 422

    ok = client.post("/translate-to-hindi", headers=headers, json={"text": "Use a hash map."}).json()
    assert ok == {"translated_text": "Use a hash map.", "translated": False, "cached": False}


def test_health_reports_without_secrets(client):
    data = client.get("/health").json()
    assert data["status"] == "ok"
    assert "key" not in str(data).lower()


def test_request_id_header_is_returned(client):
    response = client.get("/health", headers={"X-Request-ID": "abc12345-test"})
    assert response.headers["X-Request-ID"] == "abc12345-test"
    generated = client.get("/health", headers={"X-Request-ID": "bad id!"})
    assert generated.headers["X-Request-ID"] != "bad id!"
