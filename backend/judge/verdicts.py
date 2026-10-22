"""Turn a raw execution outcome + harness output into a judge verdict."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

RESULT_PREFIX = "__CV_RESULT__"

ACCEPTED = "Accepted"
WRONG_ANSWER = "Wrong Answer"
TIME_LIMIT = "Time Limit Exceeded"
MEMORY_LIMIT = "Memory Limit Exceeded"
OUTPUT_LIMIT = "Output Limit Exceeded"
RUNTIME_ERROR = "Runtime Error"
COMPILATION_ERROR = "Compilation Error"
INTERNAL_ERROR = "Internal Error"

ALL_VERDICTS = (ACCEPTED, WRONG_ANSWER, TIME_LIMIT, MEMORY_LIMIT, OUTPUT_LIMIT,
                RUNTIME_ERROR, COMPILATION_ERROR, INTERNAL_ERROR)

# How many leading tests are "sample" tests whose full input/expected output is shown.
SAMPLE_TESTS = 1

_DISPLAY_STATUS = {
    "passed": "Passed",
    "wrong_answer": "Failed",
    "runtime_error": "Failed (Runtime Error)",
    "memory_exceeded": "Failed (Memory Limit)",
}


@dataclass
class ExecutionOutcome:
    """What the executor observed about the sandboxed process."""

    status: str  # ok | timeout | memory | output_limit | crashed | internal_error
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_ms: float = 0.0
    detail: str = ""
    extra: dict = field(default_factory=dict)


def parse_harness_output(stdout: str) -> dict | None:
    for line in reversed((stdout or "").splitlines()):
        if line.startswith(RESULT_PREFIX):
            try:
                return json.loads(line[len(RESULT_PREFIX):])
            except ValueError:
                return None
    return None


def _visible_cases(results: list[dict], reveal_all: bool = False) -> list[dict]:
    first_failure = next((i for i, r in enumerate(results) if r["status"] != "passed"), None)
    cases = []
    for index, result in enumerate(results):
        # Curated bank tests are hidden; AI-generated sample tests are all shown.
        visible = reveal_all or index < SAMPLE_TESTS or index == first_failure
        case = {
            "status": _DISPLAY_STATUS.get(result["status"], "Failed"),
            "time_ms": result.get("time_ms"),
            "hidden": not visible,
        }
        if visible:
            case.update(
                input=result["input"],
                expected_output=result["expected_output"],
                actual_output=result["actual_output"],
            )
        else:
            case.update(input=f"Hidden test #{index + 1}", expected_output="hidden", actual_output="hidden")
        cases.append(case)
    return cases


def _error_kind(verdict: str, error: str) -> str:
    if verdict == COMPILATION_ERROR:
        return "syntax_error" if error.startswith(("SyntaxError", "IndentationError", "TabError")) else "signature_mismatch"
    return {
        RUNTIME_ERROR: "runtime_error", TIME_LIMIT: "time_limit", MEMORY_LIMIT: "memory_limit",
        OUTPUT_LIMIT: "output_limit", INTERNAL_ERROR: "internal_error",
    }.get(verdict, "")


def _result(verdict, *, total, passed=0, test_cases=None, error="", outcome=None, status="finished"):
    return {
        "status": status,
        "verdict": verdict,
        "error_kind": _error_kind(verdict, error or ""),
        "passed": passed,
        "total": total,
        "all_passed": verdict == ACCEPTED,
        "test_cases": test_cases or [],
        "error": (error or "")[:2000],
        "duration_ms": round(outcome.duration_ms, 1) if outcome else 0.0,
    }


def _summary_case(verdict, message, reveal_all=False):
    return [{
        "input": "All sample tests" if reveal_all else "Hidden tests",
        "expected_output": "Program finishes within the limits",
        "actual_output": message,
        "status": f"Failed ({verdict})",
        "hidden": False,
    }]


def build_judge_result(outcome: ExecutionOutcome, total_tests: int, reveal_all: bool = False) -> dict:
    if outcome.status == "internal_error":
        # Infrastructure problem, not the student's fault: no verdict, no score.
        return _result(INTERNAL_ERROR, total=total_tests, error=outcome.detail, outcome=outcome, status="error")
    if outcome.status == "timeout":
        return _result(TIME_LIMIT, total=total_tests, outcome=outcome,
                       test_cases=_summary_case(TIME_LIMIT, "Time Limit Exceeded", reveal_all))
    if outcome.status == "memory":
        return _result(MEMORY_LIMIT, total=total_tests, outcome=outcome,
                       test_cases=_summary_case(MEMORY_LIMIT, "Memory Limit Exceeded", reveal_all))
    if outcome.status == "output_limit":
        return _result(OUTPUT_LIMIT, total=total_tests, outcome=outcome,
                       test_cases=_summary_case(OUTPUT_LIMIT, "Too much output", reveal_all))

    harness = parse_harness_output(outcome.stdout)
    if harness is None:
        message = (outcome.stderr or outcome.detail or "Program crashed before reporting results").strip()
        return _result(RUNTIME_ERROR, total=total_tests, error=message[-2000:], outcome=outcome,
                       test_cases=_summary_case(RUNTIME_ERROR, message[-300:], reveal_all))

    phase = harness.get("phase")
    if phase == "compile":
        return _result(COMPILATION_ERROR, total=total_tests, error=harness.get("error", ""), outcome=outcome,
                       test_cases=_summary_case(COMPILATION_ERROR, harness.get("error", "")[:300], reveal_all))
    if phase == "load":
        verdict = MEMORY_LIMIT if harness.get("memory_exceeded") else RUNTIME_ERROR
        return _result(verdict, total=total_tests, error=harness.get("error", ""), outcome=outcome,
                       test_cases=_summary_case(verdict, harness.get("error", "")[:300], reveal_all))

    results = harness.get("results", [])
    statuses = [r["status"] for r in results]
    passed = statuses.count("passed")
    if "memory_exceeded" in statuses:
        verdict = MEMORY_LIMIT
    elif "runtime_error" in statuses:
        verdict = RUNTIME_ERROR
    elif "wrong_answer" in statuses or len(results) < total_tests:
        verdict = WRONG_ANSWER
    else:
        verdict = ACCEPTED

    first_error = next((r["actual_output"] for r in results if r["status"] == "runtime_error"), "")
    return _result(verdict, total=total_tests, passed=passed, test_cases=_visible_cases(results, reveal_all),
                   error=first_error, outcome=outcome)
