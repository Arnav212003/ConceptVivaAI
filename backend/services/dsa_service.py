"""DSA question generation and evaluation.

Scoring authority:
- Curated bank question + isolated judge available -> hidden tests decide the score
  (tier "verified"); Gemini only adds teaching feedback.
- Anything else -> rubric-based AI review (tier "ai_generated").
- AI review unavailable and no judge result -> evaluation_status "unavailable",
  score None. Nothing is invented.
"""
from __future__ import annotations

import ast
import json
from uuid import uuid4

from cache import cache_get, cache_set, make_key
from services import llm
from services.grading import safety
from services.grading.evaluators import STATUS_COMPLETED, review_code
from services.grading.prompts import AI_PRACTICE_PROBLEM, DSA_PROBLEM
from services.grading.schemas import AIPracticeProblemOutput, DSAProblemOutput
from utils import get_topic_key

# verified = hidden-test scored, ai_generated = AI-reviewed only.
TIER_VERIFIED = "verified"
TIER_AI_GENERATED = "ai_generated"

BANK_PROBLEM_TTL_SECONDS = 60 * 60 * 24


def get_question_tier(runner_supported):
    return TIER_VERIFIED if runner_supported else TIER_AI_GENERATED


def judge_available() -> bool:
    from judge.client import judge_available as _judge_available

    return _judge_available()


def is_hidden_test_available(question):
    """True only when this bank question can be scored by the isolated judge."""
    return bool(question and question.get("runner") and judge_available())


def get_default_starter_code():
    return """class Solution:
    def solve(self):
        # Write your code here
        pass"""


def get_fallback_problem_json(question):
    title = question.get("title", "DSA Problem")

    return {
        "question_id": question.get("id", ""),
        "title": title,
        "topic": question.get("topic", "DSA"),
        "difficulty": question.get("difficulty", "Medium"),
        "pattern": question.get("pattern", "General DSA"),
        "description": (
            f'Solve the problem "{title}" using the most suitable DSA technique. '
            "Think about the correct pattern and edge cases before coding.\n\n"
            "Note: the AI problem writer is currently unavailable, so this is a "
            "problem shell without a detailed statement."
        ),
        "examples": [],
        "constraints": [],
        "follow_up": "",
        "starter_code": question.get("starter_code") or get_default_starter_code(),
        "generated_by": "fallback",
    }


def _valid_ai_starter(starter: str) -> bool:
    starter = (starter or "").strip()
    if not starter.startswith("class Solution:") or "def " not in starter:
        return False
    if "def solve(" in starter or len(starter) > 1500:
        return False
    try:
        ast.parse(starter)
    except SyntaxError:
        return False
    return True


def _problem_prompt(question, enforce_signature, recent_titles, trusted_metadata):
    boundary = safety.new_boundary()
    title = question.get("title", "DSA Problem")
    fields = {
        "Title": title,
        "Topic": question.get("topic", "DSA"),
        "Difficulty": question.get("difficulty", "Medium"),
        "Pattern": question.get("pattern", "General DSA"),
    }
    metadata = "\n".join(f"{key}: {value}" for key, value in fields.items())
    parts = []
    if trusted_metadata:
        parts.append("Problem metadata (trusted, from the curated bank):\n" + metadata)
    else:
        parts.append("Problem metadata (typed by the user):\n" + safety.wrap_untrusted("metadata", metadata, boundary))

    if enforce_signature:
        parts.append(
            "starter_code must be exactly this (same class, method name and parameters):\n"
            + (question.get("starter_code") or get_default_starter_code())
        )
    else:
        parts.append(
            "starter_code: one Python `class Solution:` with a descriptive method named after "
            "what it does (never `solve`), JSON-friendly parameters, body `pass`."
        )
    parts.append(f"Variation key (vary scenario and values; never print it): {uuid4().hex[:12]}")
    if recent_titles:
        titles = "\n".join(f"- {t}" for t in recent_titles[:15])
        parts.append(
            "Recently generated titles for this topic. Produce something meaningfully different:\n"
            + safety.wrap_untrusted("recent_titles", titles, boundary)
        )
    return "\n\n".join(parts)


async def generate_dsa_problem_json_from_gemini(question, enforce_signature=True, recent_titles=None):
    """Generate a structured LeetCode-style problem. Bank statements are cached."""
    question_id = question.get("id", "")
    is_bank = bool(enforce_signature and question_id and question.get("runner"))
    cache_key = make_key("dsa_problem", DSA_PROBLEM.id, question_id) if is_bank else None

    if cache_key:
        cached = cache_get("dsa_problem", cache_key)
        if cached:
            return {**cached, "generated_by": "cache"}

    try:
        output = await llm.generate_structured(
            "dsa_problem",
            system_instruction=DSA_PROBLEM.system_instruction,
            prompt=_problem_prompt(question, enforce_signature, recent_titles, trusted_metadata=is_bank),
            schema=DSAProblemOutput,
            temperature=0.7,
        )
    except llm.LLMUnavailableError:
        return get_fallback_problem_json(question)

    result = {
        "question_id": question_id,
        "title": output.title or question.get("title", "DSA Problem"),
        "topic": question.get("topic", "DSA"),
        "difficulty": question.get("difficulty", "Medium"),
        "pattern": question.get("pattern", "General DSA"),
        "description": output.description,
        "examples": [example.model_dump() for example in output.examples],
        "constraints": list(output.constraints),
        "follow_up": output.follow_up,
        "generated_by": "ai",
    }
    if enforce_signature:
        result["starter_code"] = question.get("starter_code") or get_default_starter_code()
    else:
        result["starter_code"] = output.starter_code if _valid_ai_starter(output.starter_code) else get_default_starter_code()

    if cache_key:
        cache_set("dsa_problem", cache_key, result, BANK_PROBLEM_TTL_SECONDS)
    return result


def _no_execution(reason: str) -> dict:
    return {"available": False, "test_count": 0, "cross_check": "not_run", "reason": reason}


def ai_problem_runner(stored: dict) -> dict:
    """Harness runner config, built only from server-stored, validated data."""
    return {
        "entry": "function",
        "function": stored["function_name"],
        "tests": stored["tests"],
        "arg_types": [],
        "return_type": "raw",
        "compare": stored["compare"],
        "mutate_index": None,
    }


async def _cross_check(stored: dict, owner: str):
    """Run the AI's own reference solution on its tests inside the sandbox.

    Tests the reference disagrees with are dropped. This filters inconsistent
    tests; it does not make them ground truth (both come from the same model).
    Returns (tests, status) where status is cross_checked | reference_failed | not_run.
    """
    from judge.client import judge_and_wait

    if not stored.get("reference_solution") or not judge_available():
        return stored["tests"], "not_run"
    question = {"id": "ai_reference", "runner": ai_problem_runner(stored)}
    result = await judge_and_wait(question, stored["reference_solution"], session_id=owner, reveal_all=True)
    if not result or result.get("status") != "finished":
        return stored["tests"], "not_run"
    cases = result.get("test_cases", [])
    if len(cases) != len(stored["tests"]):
        # The reference did not reach the per-test phase (syntax/load error, TLE).
        return stored["tests"], "reference_failed"
    agreed = [test for test, case in zip(stored["tests"], cases) if case.get("status") == "Passed"]
    return agreed, "cross_checked"


async def _prepare_ai_problem(output, question: dict, owner: str):
    """Validate the generated signature/tests, cross-check, store server-side.

    Returns (public_problem_json, execution_info). Tests and the reference
    solution never leave the server except as revealed run results.
    """
    from services.ai_problem_store import new_problem_id, save_problem
    from services.dsa_generated_tests import (
        MIN_EXECUTABLE_TESTS,
        InvalidSignature,
        build_starter_code,
        compare_mode,
        format_args,
        validate_signature,
        validate_tests,
    )

    parameters = [p.model_dump() for p in output.parameters]
    problem_json = {
        "question_id": "",
        "title": output.title or question["title"],
        "topic": question["topic"],
        "difficulty": question["difficulty"],
        "pattern": question["pattern"],
        "description": output.description,
        "examples": [example.model_dump() for example in output.examples],
        "constraints": list(output.constraints),
        "follow_up": output.follow_up,
        "generated_by": "ai",
    }

    try:
        validate_signature(output.function_name, parameters, output.return_type)
    except InvalidSignature as exc:
        problem_json["starter_code"] = output.starter_code if _valid_ai_starter(output.starter_code) \
            else get_default_starter_code()
        return problem_json, _no_execution(f"The generated function signature was invalid ({exc}).")

    problem_json["starter_code"] = build_starter_code(output.function_name, parameters)
    tests, rejected = validate_tests([t.model_dump() for t in output.test_cases], parameters, output.return_type)
    stored = {
        "title": problem_json["title"],
        "topic": question["topic"],
        "difficulty": question["difficulty"],
        "function_name": output.function_name,
        "parameters": parameters,
        "return_type": output.return_type,
        "compare": compare_mode(output.return_type, output.order_matters),
        "tests": tests,
        "reference_solution": output.reference_solution,
        "rejected_count": len(rejected),
    }

    cross_check = "not_run"
    if len(tests) >= MIN_EXECUTABLE_TESTS:
        tests, cross_check = await _cross_check(stored, owner)
        stored["tests"] = tests

    executable = len(tests) >= MIN_EXECUTABLE_TESTS
    if not executable:
        reason = (
            "The AI-generated tests disagreed with the AI reference solution, so they were discarded."
            if cross_check == "cross_checked"
            else "Not enough valid AI-generated test cases could be validated for this question."
        )
        execution = _no_execution(reason)
    else:
        execution = {"available": True, "test_count": len(tests), "cross_check": cross_check, "reason": ""}
        # Show the validated tests as the examples, so the statement matches what runs.
        problem_json["examples"] = [
            {"input": format_args(parameters, t["args"]), "output": json.dumps(t["expected"]), "explanation": ""}
            for t in tests[:3]
        ]

    stored["executable"] = executable
    stored["cross_check"] = cross_check
    problem_id = new_problem_id()
    save_problem(problem_id, owner, stored)
    problem_json["practice_problem_id"] = problem_id
    return problem_json, execution


async def generate_ai_practice_question(topic, difficulty, recent_titles=None, owner=""):
    """Generate a custom-topic problem with executable AI-generated sample tests."""
    synthetic_question = {
        "id": "",
        "title": f"{topic} Practice Problem",
        "topic": topic,
        "difficulty": difficulty,
        "pattern": "AI Generated",
        "source": "AI Generated",
    }
    try:
        output = await llm.generate_structured(
            "ai_practice_problem",
            system_instruction=AI_PRACTICE_PROBLEM.system_instruction,
            prompt=_problem_prompt(synthetic_question, False, recent_titles, trusted_metadata=False),
            schema=AIPracticeProblemOutput,
            temperature=0.7,
        )
    except llm.LLMUnavailableError:
        problem_json = get_fallback_problem_json(synthetic_question)
        # Empty id keeps AI-practice questions out of the curated judge path.
        problem_json["question_id"] = ""
        return synthetic_question, problem_json, _no_execution("The AI problem writer is unavailable.")

    problem_json, execution = await _prepare_ai_problem(output, synthetic_question, owner)
    return synthetic_question, problem_json, execution


def _execution_summary(judge_result) -> str:
    if not judge_result:
        return "not run"
    if judge_result.get("status") != "finished":
        return "could not be run"
    return f"{judge_result.get('passed', 0)}/{judge_result.get('total', 0)} passed ({judge_result.get('verdict')})"


async def evaluate_ai_practice_solution(stored: dict, problem_text: str, solution: str, judge_result=None):
    """AI rubric review plus execution of the stored AI-generated sample tests.

    The score is the AI rubric score. Sample-test results are reported (and given
    to the reviewer as server-computed context) but are not a verified score.
    """
    metadata = {
        "Title": stored.get("title", "DSA Problem"),
        "Topic": stored.get("topic", "DSA"),
        "Difficulty": stored.get("difficulty", "Medium"),
        "Sample test execution (AI-generated tests, run on the server)": _execution_summary(judge_result),
    }
    review = await review_code(metadata=metadata, problem_text=problem_text, solution=solution)
    result = {**review, **_judge_fields(judge_result), "scoring_method": "ai_rubric"}
    result["execution"] = {
        "source": "ai_generated_samples",
        "verified": False,
        "cross_check": stored.get("cross_check", "not_run"),
        "available": bool(stored.get("executable")),
        "verdict": (judge_result or {}).get("verdict"),
        "passed": result["passed"],
        "total": result["total"],
    }
    # Execution ran on AI-generated tests, so it never counts as hidden-test support.
    result["runner_supported"] = False
    return result


def build_problem_text_from_json(problem_json):
    lines = [
        f"Question ID: {problem_json.get('question_id', '')}",
        "",
        f"Problem: {problem_json.get('title', 'DSA Problem')}",
        "",
        f"Difficulty: {problem_json.get('difficulty', '')}",
        f"Topic: {problem_json.get('topic', '')}",
        f"Pattern: {problem_json.get('pattern', '')}",
        "",
        "Problem Statement:",
        problem_json.get("description", ""),
    ]

    examples = problem_json.get("examples", [])
    if examples:
        lines.append("")
        lines.append("Examples:")
        for index, example in enumerate(examples, start=1):
            if not isinstance(example, dict):
                lines.append(f"Example {index}: {example}")
                continue
            lines.append(f"Example {index}:")
            lines.append(f"Input: {example.get('input', '')}")
            lines.append(f"Output: {example.get('output', '')}")
            if example.get("explanation"):
                lines.append(f"Explanation: {example.get('explanation')}")
            lines.append("")

    constraints = problem_json.get("constraints", [])
    if constraints:
        lines.append("Constraints:")
        for constraint in constraints:
            lines.append(f"- {constraint}")
        lines.append("")

    if problem_json.get("follow_up"):
        lines.append(f"Follow-up: {problem_json.get('follow_up')}")
        lines.append("")

    lines.append("Starter Code:")
    lines.append(problem_json.get("starter_code", get_default_starter_code()))
    return "\n".join(lines)


def _judge_fields(judge_result):
    if not judge_result:
        return {"test_cases": [], "runner_supported": False, "passed": 0, "total": 0, "judge": None}
    return {
        "test_cases": judge_result.get("test_cases", []),
        "runner_supported": judge_result.get("status") == "finished",
        "passed": int(judge_result.get("passed", 0) or 0),
        "total": int(judge_result.get("total", 0) or 0),
        "judge": judge_result,
    }


def score_from_judge(judge_result):
    """Hidden tests are the correctness authority: score = passed / total * 10."""
    if not judge_result or judge_result.get("status") != "finished":
        return None
    total = int(judge_result.get("total", 0) or 0)
    passed = int(judge_result.get("passed", 0) or 0)
    if total <= 0:
        return 0.0
    return round(passed * 10 / total, 1)


async def evaluate_bank_dsa_solution(question, problem_text, solution, judge_result=None):
    metadata = {
        "Title": question.get("title", "DSA Problem"),
        "Topic": question.get("topic", "DSA"),
        "Difficulty": question.get("difficulty", "Medium"),
        "Pattern": question.get("pattern", "General DSA"),
    }
    review = await review_code(metadata=metadata, problem_text=problem_text, solution=solution)
    judge_score = score_from_judge(judge_result)
    result = {**review, **_judge_fields(judge_result)}

    if judge_score is not None:
        # The judge decides the score even if AI feedback is unavailable.
        result["ai_review_status"] = review["evaluation_status"]
        result["ai_rubric_score"] = review.get("score")
        result["evaluation_status"] = STATUS_COMPLETED
        result["score"] = judge_score
        result["scoring_method"] = "hidden_tests"
        result["integrity_flags"] = review.get("integrity_flags", [])
        if review["evaluation_status"] != STATUS_COMPLETED:
            verdict = judge_result.get("verdict", "")
            result["feedback"] = (
                f"Hidden tests: {verdict} ({result['passed']}/{result['total']} passed). "
                "AI teaching feedback is unavailable right now."
            )
    else:
        result["scoring_method"] = "ai_rubric"
    return result


async def evaluate_custom_dsa_solution(request):
    metadata = {"Topic": request.topic[:100], "Difficulty": request.difficulty[:30]}
    review = await review_code(metadata=metadata, problem_text=request.problem, solution=request.solution)
    return {**review, **_judge_fields(None), "scoring_method": "ai_rubric"}


def get_fallback_dsa_problem(topic, difficulty):
    topic_key = get_topic_key(topic)

    problems = {
        "arrays": f"""
Problem: Two Sum

Difficulty: {difficulty}
Topic: Arrays

Given an array of integers nums and an integer target, return the indices of the two numbers such that they add up to target.

You may assume that each input has exactly one solution, and you may not use the same element twice.

Expected Function:
class Solution:
    def twoSum(self, nums, target):
        pass
""",
        "strings": f"""
Problem: Valid Palindrome

Difficulty: {difficulty}
Topic: Strings

Given a string s, determine whether it is a palindrome after converting all uppercase letters into lowercase letters and removing all non-alphanumeric characters.

Expected Function:
class Solution:
    def isPalindrome(self, s):
        pass
""",
        "stack": f"""
Problem: Valid Parentheses

Difficulty: {difficulty}
Topic: Stack

Given a string s containing only round, curly, and square brackets, determine if the input string is valid.

Expected Function:
class Solution:
    def isValid(self, s):
        pass
""",
        "binary search": f"""
Problem: Search Insert Position

Difficulty: {difficulty}
Topic: Binary Search

Given a sorted array of distinct integers and a target value, return the index if target is found. If not found, return the index where it would be inserted in order.

Expected Function:
class Solution:
    def searchInsert(self, nums, target):
        pass
""",
        "dynamic programming": f"""
Problem: Climbing Stairs

Difficulty: {difficulty}
Topic: Dynamic Programming

You are climbing a staircase. It takes n steps to reach the top. Each time you can climb either 1 step or 2 steps. Return the number of distinct ways to climb to the top.

Expected Function:
class Solution:
    def climbStairs(self, n):
        pass
""",
    }

    return problems.get(
        topic_key,
        f"""
Problem: Basic DSA Practice Problem

Difficulty: {difficulty}
Topic: {topic}

Solve the problem using the most suitable DSA technique.

Expected Function:
class Solution:
    def solve(self):
        pass
""",
    )
