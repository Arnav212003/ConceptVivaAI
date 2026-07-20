"""
Regression test for the DSA code runner bug: the payload used to be
dumped directly into an f-string, so JSON's true/false ended up as
bare Python identifiers in the generated script and crashed with
NameError. This locks in the fix (payload passed in as a JSON string
and parsed with json.loads inside the runner).

Uses run_python_tests directly, with ENABLE_CODE_EXECUTION forced on
for the duration of the test.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["ENABLE_CODE_EXECUTION"] = "true"

import main


def test_runner_handles_boolean_test_cases_for_strings_topic():
    solution = (
        "class Solution:\n"
        "    def isPalindrome(self, s):\n"
        "        cleaned = [c.lower() for c in s if c.isalnum()]\n"
        "        return cleaned == cleaned[::-1]"
    )

    result = main.run_python_tests("Strings", solution)

    assert result["supported"] is True
    assert result["all_passed"] is True
    assert all(case["status"] == "Passed" for case in result["test_cases"])


def test_runner_reports_failure_for_wrong_solution():
    # always returns False - should fail every palindrome test case
    solution = (
        "class Solution:\n"
        "    def isPalindrome(self, s):\n"
        "        return False"
    )

    result = main.run_python_tests("Strings", solution)

    assert result["supported"] is True
    assert result["all_passed"] is False


def test_runner_handles_arrays_topic_with_list_equality():
    solution = (
        "class Solution:\n"
        "    def twoSum(self, nums, target):\n"
        "        seen = {}\n"
        "        for i, n in enumerate(nums):\n"
        "            complement = target - n\n"
        "            if complement in seen:\n"
        "                return [seen[complement], i]\n"
        "            seen[n] = i\n"
        "        return []"
    )

    result = main.run_python_tests("Arrays", solution)

    assert result["supported"] is True
    assert result["all_passed"] is True
