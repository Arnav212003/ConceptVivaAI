"""Verdicts from the real harness running in a limited subprocess.

These use the local process runner, which on Linux CI also applies rlimits. Every
supported verdict is covered: Accepted, Wrong Answer, Runtime Error, Compilation
Error, Time Limit Exceeded, Memory Limit Exceeded and Output Limit Exceeded.
"""
import json

import pytest

from judge import verdicts as V
from judge.process_runner import Limits, run_harness
from judge.verdicts import ExecutionOutcome, build_judge_result
from services.dsa_bank import get_dsa_question_by_title

LIMITS = Limits(cpu_seconds=2, wall_seconds=4, memory_mb=256, max_processes=16, max_output_bytes=100_000)

TWO_SUM_OK = """
class Solution:
    def twoSum(self, nums, target):
        seen = {}
        for i, n in enumerate(nums):
            if target - n in seen:
                return [seen[target - n], i]
            seen[n] = i
        return []
"""


def judge(title, solution, limits=LIMITS):
    question = get_dsa_question_by_title(title)
    payload = json.dumps({"runner": question["runner"], "solution": solution})
    outcome = run_harness(payload, limits)
    return build_judge_result(outcome, len(question["runner"]["tests"]))


def test_accepted():
    result = judge("Two Sum", TWO_SUM_OK)
    assert result["verdict"] == V.ACCEPTED
    assert result["passed"] == result["total"] == 3
    assert result["all_passed"] is True


def test_wrong_answer_reveals_only_sample_and_first_failure():
    result = judge("Two Sum", "class Solution:\n    def twoSum(self, nums, target):\n        return [0, 1]\n")
    assert result["verdict"] == V.WRONG_ANSWER
    # [0, 1] happens to be correct for tests 1 and 3, wrong for test 2.
    assert result["passed"] == 2
    hidden = [case for case in result["test_cases"] if case["hidden"]]
    visible = [case for case in result["test_cases"] if not case["hidden"]]
    assert len(visible) == 2  # sample test + first failing test
    assert all(case["expected_output"] == "hidden" for case in hidden)


def test_runtime_error():
    result = judge("Two Sum", "class Solution:\n    def twoSum(self, nums, target):\n        return nums[99]\n")
    assert result["verdict"] == V.RUNTIME_ERROR
    assert "IndexError" in result["error"]


def test_compilation_error_for_syntax():
    result = judge("Two Sum", "class Solution:\n    def twoSum(self, nums, target)\n        return []\n")
    assert result["verdict"] == V.COMPILATION_ERROR
    assert "SyntaxError" in result["error"]


def test_compilation_error_for_missing_method():
    result = judge("Two Sum", "class Solution:\n    def wrongName(self, nums, target):\n        return []\n")
    assert result["verdict"] == V.COMPILATION_ERROR


def test_time_limit_exceeded():
    limits = Limits(cpu_seconds=1, wall_seconds=1.5, memory_mb=256, max_processes=16, max_output_bytes=100_000)
    result = judge("Two Sum", "class Solution:\n    def twoSum(self, nums, target):\n        while True:\n            pass\n",
                   limits)
    assert result["verdict"] == V.TIME_LIMIT
    assert result["passed"] == 0


def test_memory_limit_exceeded():
    # RLIMIT_AS turns large allocations into MemoryError on Linux; raising it
    # directly keeps the test portable to Windows developer machines.
    result = judge("Two Sum", "class Solution:\n    def twoSum(self, nums, target):\n        raise MemoryError()\n")
    assert result["verdict"] == V.MEMORY_LIMIT


def test_output_limit_exceeded():
    flood = (
        "import os\n"
        "class Solution:\n"
        "    def twoSum(self, nums, target):\n"
        "        while True:\n"
        "            os.write(1, b'x' * 65536)\n"
    )
    result = judge("Two Sum", flood)
    assert result["verdict"] == V.OUTPUT_LIMIT


def test_user_prints_do_not_corrupt_results():
    noisy = TWO_SUM_OK.replace("seen = {}", "seen = {}\n        print('__CV_RESULT__{\"fake\": true}')")
    result = judge("Two Sum", noisy)
    assert result["verdict"] == V.ACCEPTED


def test_boolean_expectations_strings_topic():
    solution = (
        "class Solution:\n"
        "    def isPalindrome(self, s):\n"
        "        cleaned = [c.lower() for c in s if c.isalnum()]\n"
        "        return cleaned == cleaned[::-1]\n"
    )
    assert judge("Valid Palindrome", solution)["verdict"] == V.ACCEPTED


def test_linked_list_arguments_and_return():
    solution = (
        "class Solution:\n"
        "    def reverseList(self, head):\n"
        "        prev = None\n"
        "        while head:\n"
        "            head.next, prev, head = prev, head, head.next\n"
        "        return prev\n"
    )
    assert judge("Reverse Linked List", solution)["verdict"] == V.ACCEPTED


def test_infrastructure_errors_have_no_verdict_score():
    result = build_judge_result(ExecutionOutcome(status="internal_error", detail="spawn failed"), 3)
    assert result["status"] == "error"
    assert result["verdict"] == V.INTERNAL_ERROR


@pytest.mark.parametrize("status,verdict", [
    ("timeout", V.TIME_LIMIT), ("memory", V.MEMORY_LIMIT), ("output_limit", V.OUTPUT_LIMIT),
])
def test_process_level_outcomes(status, verdict):
    assert build_judge_result(ExecutionOutcome(status=status), 3)["verdict"] == verdict


def test_crash_without_harness_output_is_runtime_error():
    result = build_judge_result(ExecutionOutcome(status="ok", stderr="Segmentation fault", exit_code=-11), 3)
    assert result["verdict"] == V.RUNTIME_ERROR
