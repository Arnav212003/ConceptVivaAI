"""API <-> queue <-> worker integration. A background thread plays the worker role."""
import threading

import pytest

from judge import client as judge_client
from judge.executors import LocalExecutor
from judge.process_runner import Limits
from judge.worker import Worker
from services.dsa_bank import get_dsa_question_by_title
from services.dsa_service import build_problem_text_from_json, get_fallback_problem_json
from tests.test_api_flows import start_test_session
from tests.test_judge_harness import TWO_SUM_OK


@pytest.fixture()
def judge_up(fake_redis, override_settings):
    override_settings(judge_enabled=True, judge_executor="local", judge_allow_unsafe_local=True,
                      judge_wait_seconds=15.0)
    judge_client.reset_availability_cache()
    worker = Worker(fake_redis, LocalExecutor(), Limits(cpu_seconds=2, wall_seconds=4), worker_id="t")
    stop = threading.Event()

    def loop():
        while not stop.is_set():
            worker.process_one(block_seconds=0)
            stop.wait(0.02)

    worker.process_one(block_seconds=0)  # first heartbeat
    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    yield worker
    stop.set()
    thread.join(timeout=5)
    judge_client.reset_availability_cache()


def two_sum_problem_text():
    question = get_dsa_question_by_title("Two Sum")
    return build_problem_text_from_json(get_fallback_problem_json(question)), question


def test_run_endpoint_returns_verdict(client, judge_up):
    _, headers = start_test_session(client)
    problem, question = two_sum_problem_text()
    response = client.post("/dsa/run", headers=headers, json={"problem": problem, "solution": TWO_SUM_OK})
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == "Accepted"
    assert data["question_id"] == question["id"]


def test_submit_scores_from_hidden_tests_even_without_llm(client, judge_up):
    _, headers = start_test_session(client)
    problem, _ = two_sum_problem_text()
    data = client.post("/evaluate-dsa-solution", headers=headers, json={
        "topic": "Arrays", "difficulty": "Easy", "problem": problem,
        "solution": TWO_SUM_OK, "save_attempt": True,
    }).json()

    assert data["evaluation_status"] == "completed"
    assert data["scoring_method"] == "hidden_tests"
    assert data["tier"] == "verified"
    assert data["score"] == 10.0
    assert data["judge"]["verdict"] == "Accepted"
    assert data["ai_review_status"] == "unavailable"  # no LLM in tests
    saved = data["saved_attempt"]
    assert saved["tier"] == "verified"
    assert saved["judge_verdict"] == "Accepted"
    assert saved["tests_passed"] == saved["tests_total"] == 3

    stats = client.get("/dashboard-stats", headers=headers).json()["dsa_practice"]["verified"]
    assert stats["scored_attempts"] == 1
    assert stats["average_score"] == 10.0


def test_wrong_answer_partial_score(client, judge_up):
    _, headers = start_test_session(client)
    problem, _ = two_sum_problem_text()
    data = client.post("/evaluate-dsa-solution", headers=headers, json={
        "topic": "Arrays", "difficulty": "Easy", "problem": problem,
        "solution": "class Solution:\n    def twoSum(self, nums, target):\n        return [0, 1]\n",
    }).json()
    assert data["judge"]["verdict"] == "Wrong Answer"
    assert data["score"] == round(2 * 10 / 3, 1)
    assert data["status"] == "Needs Improvement"


def test_async_submission_is_private_to_its_session(client, judge_up):
    _, owner = start_test_session(client)
    _, other = start_test_session(client)
    problem, _ = two_sum_problem_text()
    created = client.post("/dsa/submissions", headers=owner, json={"problem": problem, "solution": TWO_SUM_OK})
    assert created.status_code == 202
    submission_id = created.json()["submission_id"]

    assert client.get(f"/dsa/submissions/{submission_id}", headers=other).status_code == 404

    import time
    for _ in range(100):
        status = client.get(f"/dsa/submissions/{submission_id}", headers=owner).json()
        if status["status"] == "finished":
            break
        time.sleep(0.05)
    assert status["verdict"] == "Accepted"


def test_judge_offline_means_ai_tier_and_503_for_runs(client):
    _, headers = start_test_session(client)
    problem, _ = two_sum_problem_text()

    run = client.post("/dsa/run", headers=headers, json={"problem": problem, "solution": TWO_SUM_OK})
    assert run.status_code == 503

    data = client.post("/evaluate-dsa-solution", headers=headers, json={
        "topic": "Arrays", "difficulty": "Easy", "problem": problem, "solution": TWO_SUM_OK,
    }).json()
    # Never labelled verified when hidden tests did not run.
    assert data["tier"] == "ai_generated"
    assert data["scoring_method"] == "ai_rubric"
    assert data["score"] is None  # and no LLM either

    stats = client.get("/dsa-question-bank/stats").json()
    assert stats["hidden_tests_enabled"] is False


def test_run_rejects_non_bank_questions(client, judge_up):
    _, headers = start_test_session(client)
    response = client.post("/dsa/run", headers=headers, json={"problem": "Problem: custom", "solution": "x = 1"})
    assert response.status_code == 400


def test_judge_requires_live_worker_heartbeat(fake_redis, override_settings):
    override_settings(judge_enabled=True, judge_executor="local", judge_allow_unsafe_local=True)
    judge_client.reset_availability_cache()
    assert judge_client.judge_available() is False  # no worker heartbeat yet
    judge_client.reset_availability_cache()


def test_local_executor_refused_without_explicit_opt_in(fake_redis, override_settings):
    override_settings(judge_enabled=True, judge_executor="local", judge_allow_unsafe_local=False)
    judge_client.reset_availability_cache()
    fake_redis.set("cv:judge:heartbeat", "w", ex=30)
    assert judge_client.judge_available() is False
    judge_client.reset_availability_cache()
