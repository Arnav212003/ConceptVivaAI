"""Code execution for AI-generated DSA practice problems.

Gemini is faked; the judge runs real submissions through the Redis queue, the worker
and the harness subprocess (see the judge_up fixture).
"""
import json

import pytest

from services.dsa_generated_tests import (
    InvalidSignature,
    build_starter_code,
    check_value,
    compare_mode,
    validate_signature,
    validate_tests,
)
from tests.test_api_flows import start_test_session
from tests.test_judge_api import judge_up  # noqa: F401  (fixture)

PARAMS = [{"name": "nums", "type": "list[int]"}]
REFERENCE = (
    "class Solution:\n"
    "    def maxPairSum(self, nums):\n"
    "        # REFERENCE_MARKER\n"
    "        top = sorted(nums)\n"
    "        return top[-1] + top[-2]\n"
)
CORRECT = REFERENCE.replace("# REFERENCE_MARKER", "# student")
WRONG = "class Solution:\n    def maxPairSum(self, nums):\n        return nums[0] + nums[1]\n"
SYNTAX = "class Solution:\n    def maxPairSum(self, nums)\n        return 0\n"
TIMEOUT = "class Solution:\n    def maxPairSum(self, nums):\n        while True:\n            pass\n"

GOOD_TESTS = [
    ({"nums": [1, 2, 3]}, 5),
    ({"nums": [5, 5]}, 10),
    ({"nums": [-1, -2, -3]}, -3),
    ({"nums": [0, 4, 1, 9]}, 13),
]


def case(args, expected):
    return {"input_json": json.dumps(args), "expected_output_json": json.dumps(expected)}


def ai_problem(tests=GOOD_TESTS, **overrides):
    payload = {
        "title": "Max Pair Sum",
        "description": "Return the largest sum of two distinct elements of nums.",
        "examples": [{"input": "nums = [1,2,3]", "output": "5", "explanation": "2 + 3"}],
        "constraints": ["2 <= nums.length <= 1000"],
        "follow_up": "",
        "starter_code": "anything; the server rebuilds it",
        "function_name": "maxPairSum",
        "parameters": PARAMS,
        "return_type": "int",
        "order_matters": True,
        "test_cases": [case(a, e) if isinstance(a, dict) else a for a, e in tests] if tests and isinstance(tests[0], tuple)
        else tests,
        "reference_solution": REFERENCE,
    }
    payload.update(overrides)
    return payload


def code_review(points=4):
    return {
        "rubric": {
            "correctness": {"points": points, "rationale": "r"},
            "efficiency": {"points": 2, "rationale": "r"},
            "edge_cases": {"points": 1, "rationale": "r"},
            "code_quality": {"points": 1, "rationale": "r"},
        },
        "manipulation_attempt": False,
        "feedback": "Sorting works; a single pass would be O(n).",
        "optimized_approach": "Track the two largest values.",
        "optimized_code": "class Solution: ...",
        "explanation": "One pass.",
        "time_complexity": "O(n log n)",
        "space_complexity": "O(n)",
    }


def generate(client, headers):
    return client.post("/generate-ai-practice-question", headers=headers,
                       json={"topic": "Arrays", "difficulty": "Easy"}).json()


def run(client, headers, problem_id, solution, **extra):
    return client.post("/dsa/run", headers=headers,
                       json={"practice_problem_id": problem_id, "solution": solution, **extra})


# ------------------------------------------------------------------ validation


def test_type_checks_are_strict():
    assert check_value(3, "int") and not check_value(True, "int") and not check_value(3.5, "int")
    assert check_value(2, "float") and not check_value(float("nan"), "float")
    assert check_value([[1, 2], [3]], "list[list[int]]") and not check_value([[1, "2"]], "list[list[int]]")
    assert check_value(["a"], "list[str]") and not check_value("a", "list[str]")
    assert not check_value(10**13, "int")
    assert not check_value(list(range(1001)), "list[int]")


def test_malformed_and_inconsistent_tests_are_dropped():
    raw = [
        case({"nums": [1, 2]}, 3),
        {"input_json": "{not json", "expected_output_json": "3"},
        case({"numbers": [1, 2]}, 3),                 # wrong parameter name
        case({"nums": [1, True]}, 2),                 # bool is not int
        case({"nums": [1, 2]}, "3"),                  # wrong return type
        case({"nums": [4, 4]}, 8),
        case({"nums": [4, 4]}, 9),                    # same input, different answer
        case({"nums": [1, 2]}, 3),                    # exact duplicate
        {"input_json": json.dumps([[7, 1]]), "expected_output_json": "8"},  # positional form
    ]
    accepted, rejected = validate_tests(raw, PARAMS, "int")
    assert accepted == [{"args": [[1, 2]], "expected": 3}, {"args": [[7, 1]], "expected": 8}]
    assert len(rejected) >= 6


@pytest.mark.parametrize("name,params", [
    ("class", PARAMS),
    ("maxPairSum", [{"name": "self", "type": "int"}]),
    ("maxPairSum", [{"name": "a", "type": "int"}, {"name": "a", "type": "int"}]),
    ("__import__", PARAMS),
    ("max pair", PARAMS),
])
def test_invalid_signatures_are_rejected(name, params):
    with pytest.raises(InvalidSignature):
        validate_signature(name, params, "int")


def test_starter_code_and_compare_mode_come_from_the_validated_signature():
    assert "def maxPairSum(self, nums: List[int]):" in build_starter_code("maxPairSum", PARAMS)
    assert compare_mode("float", True) == "approx"
    assert compare_mode("list[int]", False) == "unordered_outer"
    assert compare_mode("list[int]", True) == "exact"


# ------------------------------------------------------------------ generation


def test_generation_stores_tests_server_side_and_never_returns_them(client, fake_llm):
    fake_llm.responses["AIPracticeProblemOutput"] = ai_problem()
    _, headers = start_test_session(client)
    data = generate(client, headers)

    problem = data["problem_json"]
    assert problem["practice_problem_id"].startswith("aip_")
    assert data["tier"] == "ai_generated"
    assert data["execution"] == {"available": True, "test_count": 4, "cross_check": "not_run", "reason": ""}
    assert problem["starter_code"].startswith("class Solution:\n    def maxPairSum(self, nums: List[int]):")
    # The statement shows validated tests, so it matches what actually runs.
    assert problem["examples"][0] == {"input": "nums = [1, 2, 3]", "output": "5", "explanation": ""}
    serialized = json.dumps(data)
    assert "REFERENCE_MARKER" not in serialized and "reference_solution" not in serialized
    assert "test_cases" not in problem


def test_generation_with_malformed_tests_falls_back_to_ai_review(client, fake_llm):
    fake_llm.responses["AIPracticeProblemOutput"] = ai_problem(
        tests=[{"input_json": "oops", "expected_output_json": "1"}, case({"nums": "x"}, 1)]
    )
    _, headers = start_test_session(client)
    data = generate(client, headers)
    assert data["execution"]["available"] is False
    assert "Not enough valid" in data["execution"]["reason"]
    response = run(client, headers, data["problem_json"]["practice_problem_id"], CORRECT)
    assert response.status_code == 409


def test_generation_with_invalid_signature_is_not_executable(client, fake_llm):
    fake_llm.responses["AIPracticeProblemOutput"] = ai_problem(function_name="def")
    _, headers = start_test_session(client)
    data = generate(client, headers)
    assert data["execution"]["available"] is False
    assert "practice_problem_id" not in data["problem_json"]


def test_cross_check_drops_tests_the_reference_disagrees_with(client, fake_llm, judge_up):
    wrong_expected = GOOD_TESTS + [({"nums": [2, 2, 2]}, 6)]  # correct answer is 4
    fake_llm.responses["AIPracticeProblemOutput"] = ai_problem(tests=wrong_expected)
    _, headers = start_test_session(client)
    data = generate(client, headers)
    assert data["execution"]["cross_check"] == "cross_checked"
    assert data["execution"]["test_count"] == 4


def test_mostly_wrong_tests_make_the_problem_non_executable(client, fake_llm, judge_up):
    bad = [({"nums": [1, 2]}, 99), ({"nums": [3, 4]}, 98), ({"nums": [5, 6]}, 11)]
    fake_llm.responses["AIPracticeProblemOutput"] = ai_problem(tests=bad)
    _, headers = start_test_session(client)
    data = generate(client, headers)
    assert data["execution"]["available"] is False
    assert "disagreed" in data["execution"]["reason"]


def test_broken_reference_keeps_tests_but_reports_it(client, fake_llm, judge_up):
    fake_llm.responses["AIPracticeProblemOutput"] = ai_problem(reference_solution="class Solution:\n  def oops(")
    _, headers = start_test_session(client)
    data = generate(client, headers)
    assert data["execution"]["available"] is True
    assert data["execution"]["cross_check"] == "reference_failed"


# ------------------------------------------------------------------ run


@pytest.fixture()
def ai_session(client, fake_llm, judge_up):
    fake_llm.responses["AIPracticeProblemOutput"] = ai_problem()
    _, headers = start_test_session(client)
    data = generate(client, headers)
    return headers, data["problem_json"]["practice_problem_id"], data


def test_run_correct_solution_shows_every_sample(client, ai_session):
    headers, problem_id, _ = ai_session
    data = run(client, headers, problem_id, CORRECT).json()
    assert data["verdict"] == "Accepted"
    assert (data["passed"], data["total"]) == (4, 4)
    assert data["test_source"] == "ai_generated_samples"
    assert data["cross_check"] == "cross_checked"
    first = data["test_cases"][0]
    assert first["hidden"] is False
    assert (first["input"], first["expected_output"], first["actual_output"]) == ("[[1, 2, 3]]", "5", "5")
    assert all(c["status"] == "Passed" and not c["hidden"] for c in data["test_cases"])


def test_run_wrong_answer_shows_failing_details(client, ai_session):
    headers, problem_id, _ = ai_session
    data = run(client, headers, problem_id, WRONG).json()
    assert data["verdict"] == "Wrong Answer"
    failing = [c for c in data["test_cases"] if c["status"] == "Failed"]
    assert failing and failing[0]["actual_output"] != failing[0]["expected_output"]
    assert all(not c["hidden"] for c in data["test_cases"])


def test_run_syntax_error(client, ai_session):
    headers, problem_id, _ = ai_session
    data = run(client, headers, problem_id, SYNTAX).json()
    assert data["verdict"] == "Compilation Error"
    assert data["error_kind"] == "syntax_error"
    assert "SyntaxError" in data["error"]
    assert data["test_cases"][0]["input"] == "All sample tests"  # not "Hidden tests"


def test_run_timeout(client, ai_session):
    headers, problem_id, _ = ai_session
    data = run(client, headers, problem_id, TIMEOUT).json()
    assert data["verdict"] == "Time Limit Exceeded"
    assert data["error_kind"] == "time_limit"


def test_run_ignores_browser_supplied_tests_and_saves_nothing(client, ai_session):
    headers, problem_id, _ = ai_session
    forged = {"tests": [{"args": [[1]], "expected": 1}], "runner": {"function": "evil"}, "compare": "any_of"}
    data = run(client, headers, problem_id, CORRECT, **forged).json()
    assert data["total"] == 4  # the stored tests, not the forged one
    stats = client.get("/dashboard-stats", headers=headers).json()["dsa_practice"]
    assert stats["total_attempts"] == 0


def test_problem_is_bound_to_its_session(client, ai_session):
    _, problem_id, _ = ai_session
    _, other = start_test_session(client)
    assert run(client, other, problem_id, CORRECT).status_code == 404
    assert run(client, other, "aip_" + "0" * 24, CORRECT).status_code == 404


def test_problem_expires(client, ai_session, fake_redis):
    from services.ai_problem_store import PROBLEM_TTL_SECONDS

    headers, problem_id, _ = ai_session
    key = f"cv:aiq:{problem_id}"
    assert 0 < fake_redis.ttl(key) <= PROBLEM_TTL_SECONDS
    fake_redis.delete(key)  # what Redis does when the TTL runs out
    response = run(client, headers, problem_id, CORRECT)
    assert response.status_code == 404
    assert "expired" in response.json()["detail"]


def test_run_with_judge_offline_is_503(client, fake_llm):
    fake_llm.responses["AIPracticeProblemOutput"] = ai_problem()
    _, headers = start_test_session(client)
    problem_id = generate(client, headers)["problem_json"]["practice_problem_id"]
    assert run(client, headers, problem_id, CORRECT).status_code == 503


# ------------------------------------------------------------------ submit


def submit(client, headers, problem_id, solution):
    return client.post("/evaluate-dsa-solution", headers=headers, json={
        "topic": "Arrays", "difficulty": "Easy", "problem": "Problem: Max Pair Sum", "solution": solution,
        "mode": "Practice", "save_attempt": True, "practice_problem_id": problem_id,
    }).json()


def test_submit_runs_samples_reviews_and_saves_without_verified_label(client, fake_llm, ai_session):
    headers, problem_id, _ = ai_session
    fake_llm.responses["CodeReviewOutput"] = code_review(points=5)
    data = submit(client, headers, problem_id, CORRECT)

    assert data["evaluation_status"] == "completed"
    assert data["score"] == 9.0                     # AI rubric, not test pass rate
    assert data["scoring_method"] == "ai_rubric"
    assert data["tier"] == "ai_generated"           # never "verified" for AI-generated tests
    assert data["execution"] == {
        "source": "ai_generated_samples", "verified": False, "cross_check": "cross_checked",
        "available": True, "verdict": "Accepted", "passed": 4, "total": 4,
    }
    review_prompt = fake_llm.calls[-1]["prompt"]
    assert "Sample test execution" in review_prompt and "4/4 passed (Accepted)" in review_prompt

    saved = data["saved_attempt"]
    assert (saved["tier"], saved["judge_verdict"], saved["tests_passed"], saved["tests_total"]) == \
        ("ai_generated", "Accepted", 4, 4)
    assert saved["test_source"] == "ai_generated_samples"
    assert saved["problem_name"] == "Max Pair Sum"

    stats = client.get("/dashboard-stats", headers=headers).json()["dsa_practice"]
    assert stats["verified"]["total_attempts"] == 0
    assert stats["ai_generated"]["scored_attempts"] == 1
    history = client.get("/history", headers=headers).json()["dsa_practice"]
    assert history[0]["test_source"] == "ai_generated_samples"


def test_submit_wrong_code_keeps_execution_and_rubric_separate(client, fake_llm, ai_session):
    headers, problem_id, _ = ai_session
    fake_llm.responses["CodeReviewOutput"] = code_review(points=1)
    data = submit(client, headers, problem_id, WRONG)
    assert data["execution"]["verdict"] == "Wrong Answer"
    assert data["execution"]["passed"] < 4
    assert data["score"] == 5.0
    assert data["status"] == "Needs Improvement"


def test_submit_without_ai_review_is_unscored_but_keeps_execution(client, ai_session):
    from services import llm

    llm.set_llm_backend(None)
    headers, problem_id, _ = ai_session
    data = submit(client, headers, problem_id, CORRECT)
    assert data["evaluation_status"] == "unavailable"
    assert data["score"] is None
    assert data["execution"]["verdict"] == "Accepted"
    assert data["saved_attempt"]["judge_verdict"] == "Accepted"
    assert data["saved_attempt"]["score"] is None


def test_submit_with_unknown_problem_id_is_404(client):
    _, headers = start_test_session(client)
    response = client.post("/evaluate-dsa-solution", headers=headers, json={
        "topic": "Arrays", "difficulty": "Easy", "problem": "x", "solution": CORRECT,
        "practice_problem_id": "aip_" + "f" * 24,
    })
    assert response.status_code == 404


# ------------------------------------------------------------------ every supported type

from typing import get_args  # noqa: E402

from services.dsa_generated_tests import SUPPORTED_TYPES, python_type_hint  # noqa: E402
from services.grading.schemas import ValueType  # noqa: E402

# One valid and one invalid sample per ValueType. Adding a type to the schema
# without adding it here makes test_every_value_type_has_samples fail.
TYPE_SAMPLES = {
    "int": (7, True),
    "float": (2.5, "2.5"),
    "str": ("abc", 3),
    "bool": (False, 0),
    "list[int]": ([1, 2], [1, False]),
    "list[float]": ([1.5, 2], [1.5, "x"]),
    "list[str]": (["a", "b"], ["a", 1]),
    "list[bool]": ([True, False], [True, 1]),
    "list[list[int]]": ([[1], [2, 3]], [[1], [True]]),
    "list[list[str]]": ([["a"], []], [["a", 2]]),
}


def test_every_value_type_has_samples():
    assert set(TYPE_SAMPLES) == set(get_args(ValueType)) == SUPPORTED_TYPES


@pytest.mark.parametrize("type_name", get_args(ValueType))
def test_every_value_type_builds_valid_starter_code(type_name):
    import ast

    params = [{"name": "value", "type": type_name}, {"name": "k", "type": "int"}]
    validate_signature("useValue", params, type_name)  # no exception
    code = build_starter_code("useValue", params)
    assert f"def useValue(self, value: {python_type_hint(type_name)}, k: int):" in code
    ast.parse("from typing import List\n" + code)


@pytest.mark.parametrize("type_name", get_args(ValueType))
def test_every_value_type_validates_values_and_tests(type_name):
    good, bad = TYPE_SAMPLES[type_name]
    assert check_value(good, type_name) is True
    assert check_value(bad, type_name) is False

    params = [{"name": "value", "type": type_name}]
    accepted, _ = validate_tests(
        [case({"value": good}, good), case({"value": bad}, good)], params, type_name
    )
    assert accepted == [{"args": [good], "expected": good}]


@pytest.mark.parametrize("bad_type", ["list[dict]", "dict", "list[list[float]]", "None", "", "List[int]"])
def test_unknown_types_are_rejected_without_key_errors(bad_type):
    with pytest.raises(InvalidSignature):
        validate_signature("f", [{"name": "x", "type": bad_type}], "int")
    with pytest.raises(InvalidSignature):
        validate_signature("f", [{"name": "x", "type": "int"}], bad_type)
    with pytest.raises(InvalidSignature):
        build_starter_code("f", [{"name": "x", "type": bad_type}])
    assert check_value([1], bad_type) is False


def test_list_bool_problem_runs_end_to_end(client, fake_llm, judge_up):
    fake_llm.responses["AIPracticeProblemOutput"] = ai_problem(
        tests=[({"flags": [True, False, True]}, 2), ({"flags": []}, 0), ({"flags": [False]}, 0)],
        function_name="countTrue",
        parameters=[{"name": "flags", "type": "list[bool]"}],
        return_type="int",
        reference_solution="class Solution:\n    def countTrue(self, flags):\n        return sum(flags)\n",
    )
    _, headers = start_test_session(client)
    data = generate(client, headers)
    assert data["execution"] == {"available": True, "test_count": 3, "cross_check": "cross_checked", "reason": ""}
    assert "def countTrue(self, flags: List[bool]):" in data["problem_json"]["starter_code"]
    result = run(client, headers, data["problem_json"]["practice_problem_id"],
                 "class Solution:\n    def countTrue(self, flags):\n        return flags.count(True)\n").json()
    assert (result["verdict"], result["passed"], result["total"]) == ("Accepted", 3, 3)
