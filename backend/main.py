import os
import json
import re
import sys
import tempfile
import subprocess
from pathlib import Path

from dotenv import load_dotenv

from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from sqlalchemy.orm import Session

from database import Base, engine, get_db
import models

from crud import (
    create_dsa_attempt,
    create_interview_report,
    create_ml_practice_attempt,
    create_project_attempt,
    create_project_challenge,
    decode_project_challenge,
    get_dashboard_stats,
    get_project_challenge_by_id,
    get_user_history,
    mark_project_challenge_completed,
)

from security import (
    create_session_credentials,
    get_current_session_id,
    revoke_session_token,
)


try:
    from data.dsa_question import (
        DSA_QUESTION_BANK,
        get_all_dsa_questions,
        get_dsa_questions_by_difficulty,
        get_dsa_questions_by_topic,
        get_dsa_questions_by_topic_and_difficulty,
        get_dsa_question_by_id,
        get_dsa_question_by_title,
        get_dsa_mock_set,
        get_dsa_practice_question,
    )
except Exception:
    DSA_QUESTION_BANK = []

    def get_all_dsa_questions():
        return []

    def get_dsa_questions_by_difficulty(difficulty):
        return []

    def get_dsa_questions_by_topic(topic):
        return []

    def get_dsa_questions_by_topic_and_difficulty(topic, difficulty):
        return []

    def get_dsa_question_by_id(question_id):
        return None

    def get_dsa_question_by_title(title):
        return None

    def get_dsa_mock_set(topic="Arrays", difficulty="Mixed", count=10):
        return []

    def get_dsa_practice_question(topic="Arrays", difficulty="Mixed"):
        return None


# the old relative path "../.env.local" depended on the current working
# directory, so switched to an absolute Path-based load like security.py
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env.local")
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
ENABLE_CODE_EXECUTION = os.getenv("ENABLE_CODE_EXECUTION", "false").lower() == "true"

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

app = FastAPI(title="ConceptVivaAI Backend")

Base.metadata.create_all(bind=engine)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.29.17:3000",
        FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/session/start")
def start_session():
    return create_session_credentials()


@app.post("/session/logout")
def logout_session(
    session_id: str = Depends(get_current_session_id),
    x_session_token: str = Header(default="", alias="X-Session-Token"),
    db: Session = Depends(get_db),
):
    if not x_session_token:
        raise HTTPException(
            status_code=401,
            detail="Missing session token.",
        )

    revoke_session_token(
        db=db,
        session_id=session_id,
        session_token=x_session_token,
        reason="User logout",
    )

    return {
        "message": "Session logged out successfully.",
        "session_id": session_id,
        "revoked": True,
    }


class QuestionRequest(BaseModel):
    topic: str
    level: str


class EvaluateRequest(BaseModel):
    topic: str
    level: str
    question: str
    answer: str


class DSAProblemRequest(BaseModel):
    topic: str
    difficulty: str


class DSAEvaluateRequest(BaseModel):
    topic: str
    difficulty: str
    problem: str
    solution: str


class DSAMockSetRequest(BaseModel):
    topic: str = "Arrays"
    difficulty: str = "Mixed"
    count: int = 10


class DSAPracticeQuestionRequest(BaseModel):
    topic: str = "Arrays"
    difficulty: str = "Mixed"


class DSAOwnQuestionRequest(BaseModel):
    title: str
    topic: str = "Arrays"
    difficulty: str = "Medium"
    pattern: str = "General DSA"


class SaveMLPracticeAttemptRequest(BaseModel):
    session_id: str = ""
    topic: str
    level: str
    question: str
    answer: str
    score: float = 0
    verdict: str = "PARTIAL"
    feedback: str = ""
    missing_points: str = ""
    corrected_answer: str = ""
    improvement: str = ""


class SaveInterviewReportRequest(BaseModel):
    session_id: str = ""
    topic: str
    level: str
    rounds: int = 0
    average_score: float = 0
    strong_points: str = ""
    weak_points: str = ""
    recommendation: str = ""


class SaveDSAAttemptRequest(BaseModel):
    session_id: str = ""
    mode: str = "Practice"
    topic: str
    difficulty: str
    problem_name: str = "DSA Problem"
    problem: str = ""
    solution: str = ""
    score: float = 0
    status: str = "Needs Improvement"
    feedback: str = ""


class SaveProjectAttemptRequest(BaseModel):
    session_id: str = ""
    challenge_id: str = ""

    domain: str = "Machine Learning"
    topic: str = "AI Selected Topic"
    difficulty: str = "Beginner"
    project_title: str = "Project Challenge"
    challenge: dict = Field(default_factory=dict)
    submission: str = ""
    score: float = 0
    verdict: str = "PARTIAL"
    feedback: str = ""
    missing_points: str = ""
    improved_approach: str = ""
    next_steps: str = ""


def extract_json(text):
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{[\s\S]*\}", text)

        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None

        return None


def get_topic_key(topic):
    return topic.lower().strip()


def extract_question_id_from_problem_text(problem_text):
    if not problem_text:
        return None

    match = re.search(r"Question ID:\s*(\S+)", problem_text)

    if match:
        return match.group(1).strip()

    match = re.search(r"Problem ID:\s*(\S+)", problem_text)

    if match:
        return match.group(1).strip()

    return None


def get_difficulty_distribution(questions):
    easy = 0
    medium = 0
    hard = 0

    for question in questions:
        difficulty = question.get("difficulty", "").lower().strip()

        if difficulty == "easy":
            easy += 1
        elif difficulty == "medium":
            medium += 1
        elif difficulty == "hard":
            hard += 1

    return {
        "easy": easy,
        "medium": medium,
        "hard": hard,
        "total": len(questions),
    }


def format_datetime(value):
    if not value:
        return ""

    try:
        return value.isoformat()
    except Exception:
        return str(value)


def serialize_ml_attempt(item):
    return {
        "id": item.id,
        "session_id": item.session_id,
        "topic": item.topic,
        "level": item.level,
        "question": item.question,
        "answer": item.answer,
        "score": item.score,
        "verdict": item.verdict,
        "feedback": item.feedback,
        "missing_points": item.missing_points,
        "corrected_answer": item.corrected_answer,
        "improvement": item.improvement,
        "created_at": format_datetime(item.created_at),
    }


def serialize_interview_report(item):
    return {
        "id": item.id,
        "session_id": item.session_id,
        "topic": item.topic,
        "level": item.level,
        "rounds": item.rounds,
        "average_score": item.average_score,
        "strong_points": item.strong_points,
        "weak_points": item.weak_points,
        "recommendation": item.recommendation,
        "created_at": format_datetime(item.created_at),
    }


def serialize_dsa_attempt(item):
    return {
        "id": item.id,
        "session_id": item.session_id,
        "mode": item.mode,
        "topic": item.topic,
        "difficulty": item.difficulty,
        "problem_name": item.problem_name,
        "problem": item.problem,
        "solution": item.solution,
        "score": item.score,
        "status": item.status,
        "feedback": item.feedback,
        "created_at": format_datetime(item.created_at),
    }


def serialize_project_attempt(item):
    challenge_data = decode_project_challenge(item.challenge_json)

    return {
        "id": item.id,
        "session_id": item.session_id,
        "challenge_id": item.challenge_id,
        "domain": item.domain,
        "topic": item.topic,
        "difficulty": item.difficulty,
        "project_title": item.project_title,
        "challenge": challenge_data,
        "challenge_json": challenge_data,
        "submission": item.submission,
        "score": item.score,
        "verdict": item.verdict,
        "feedback": item.feedback,
        "missing_points": item.missing_points,
        "improved_approach": item.improved_approach,
        "next_steps": item.next_steps,
        "created_at": format_datetime(item.created_at),
    }


def get_default_starter_code():
    return """class Solution:
    def solve(self):
        # Write your code here
        pass"""


def get_fallback_problem_json(question):
    # returns the same JSON shape even when Gemini is unavailable or fails,
    # so the frontend never has to handle a different response format

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
            "Note: Gemini API is currently unavailable, so this is a fallback "
            "problem shell without detailed statement."
        ),
        "examples": [],
        "constraints": [],
        "follow_up": "",
        "starter_code": get_default_starter_code(),
    }


def generate_dsa_problem_json_from_gemini(question):
    # generates a LeetCode-style structured question.
    # earlier this returned plain text which just looked like one big blob
    # on the frontend, so now it returns JSON and the UI can render proper
    # sections (title, examples, constraints, etc.)

    title = question.get("title", "DSA Problem")
    topic = question.get("topic", "DSA")
    difficulty = question.get("difficulty", "Medium")
    pattern = question.get("pattern", "General DSA")
    question_id = question.get("id", "")

    if not GEMINI_API_KEY or not client:
        return get_fallback_problem_json(question)

    prompt = f"""
You are ConceptVivaAI, a strict DSA practice problem generator.

Generate a coding practice problem in the exact style and tone of LeetCode.

Question metadata:
Question ID: {question_id}
Title: {title}
Topic: {topic}
Difficulty: {difficulty}
Pattern: {pattern}

Very important rules:
1. Do NOT provide the solution or optimized code.
2. Do NOT explain the answer.
3. The problem must read exactly like a real LeetCode problem page.
4. Give 2-3 examples. Each example must have input, output, and a short explanation.
5. Constraints must look like LeetCode constraints, for example "1 <= nums.length <= 10^4".
6. Starter code must be Python, using class Solution with a natural function name for this problem.
7. In the description, keep paragraphs short and clear. Refer to variables like nums, target, s, n naturally.
8. Stay strictly aligned with the given title, topic, difficulty, and pattern. Do not invent a different problem.
9. follow_up is optional. If a natural follow-up exists (like a better complexity), include it, otherwise return empty string.

Return only valid JSON in this exact format:
{{
  "question_id": "{question_id}",
  "title": "{title}",
  "difficulty": "{difficulty}",
  "topic": "{topic}",
  "pattern": "{pattern}",
  "description": "LeetCode-style problem description with short clear paragraphs",
  "examples": [
    {{
      "input": "nums = [2,7,11,15], target = 9",
      "output": "[0,1]",
      "explanation": "Because nums[0] + nums[1] == 9, we return [0, 1]."
    }}
  ],
  "constraints": [
    "2 <= nums.length <= 10^4",
    "-10^9 <= nums[i] <= 10^9"
  ],
  "follow_up": "optional follow-up question or empty string",
  "starter_code": "class Solution:\\n    def functionName(self, ...):\\n        # Write your code here\\n        pass"
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        result = extract_json(response.text)

        if not result:
            return get_fallback_problem_json(question)

        # force-set question_id because the evaluation step looks up
        # the question in the bank using this exact id
        result["question_id"] = question_id

        result.setdefault("title", title)
        result.setdefault("difficulty", difficulty)
        result.setdefault("topic", topic)
        result.setdefault("pattern", pattern)
        result.setdefault("description", f'Solve the problem "{title}".')
        result.setdefault("examples", [])
        result.setdefault("constraints", [])
        result.setdefault("follow_up", "")
        result.setdefault("starter_code", get_default_starter_code())

        if not isinstance(result["examples"], list):
            result["examples"] = []

        if not isinstance(result["constraints"], list):
            result["constraints"] = []

        return result

    except Exception:
        return get_fallback_problem_json(question)


def build_problem_text_from_json(problem_json):
    # builds a plain text version from the JSON.
    # needed for the evaluation flow, since the frontend sends back the
    # problem text when evaluating, and the backend extracts the Question ID
    # from that text

    lines = []

    lines.append(f"Question ID: {problem_json.get('question_id', '')}")
    lines.append("")
    lines.append(f"Problem: {problem_json.get('title', 'DSA Problem')}")
    lines.append("")
    lines.append(f"Difficulty: {problem_json.get('difficulty', '')}")
    lines.append(f"Topic: {problem_json.get('topic', '')}")
    lines.append(f"Pattern: {problem_json.get('pattern', '')}")
    lines.append("")
    lines.append("Problem Statement:")
    lines.append(problem_json.get("description", ""))

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


def evaluate_bank_dsa_solution_with_gemini(question, problem_text, solution):
    title = question.get("title", "DSA Problem")
    topic = question.get("topic", "DSA")
    difficulty = question.get("difficulty", "Medium")
    pattern = question.get("pattern", "General DSA")

    if not GEMINI_API_KEY or not client:
        return {
            "score": 6,
            "feedback": "Your solution was received. Gemini API is unavailable right now, so detailed AI evaluation could not run.",
            "optimized_approach": "Use the correct DSA pattern for this problem and verify edge cases.",
            "optimized_code": "Gemini optimized code is unavailable right now.",
            "explanation": "Evaluation will be generated by Gemini when API is available.",
            "time_complexity": "Depends on solution",
            "space_complexity": "Depends on solution",
            "test_cases": [
                {
                    "input": "AI evaluation mode",
                    "expected_output": "Gemini generated feedback",
                    "actual_output": "Gemini unavailable",
                    "status": "Not Executed",
                }
            ],
        }

    prompt = f"""
You are ConceptVivaAI, a strict DSA code evaluator.

Evaluate the user's code for the selected curated DSA question.

Question metadata:
Title: {title}
Topic: {topic}
Difficulty: {difficulty}
Pattern: {pattern}

Problem:
{problem_text}

User Solution:
{solution}

Evaluation rules:
1. Check whether the code solves the given problem.
2. Check logic, edge cases, time complexity, and space complexity.
3. If code is wrong, explain the mistake clearly.
4. Provide optimized approach and complete optimized Python code.
5. Generate 3 meaningful test cases and mark likely pass/fail if possible.
6. Be strict but helpful.
7. Do not depend on exact wording. Judge logic.

Return only valid JSON in this exact format:
{{
  "score": number from 0 to 10,
  "feedback": "clear feedback about correctness, logic, and missing cases",
  "optimized_approach": "best optimized approach explained clearly",
  "optimized_code": "complete optimized Python code",
  "explanation": "explain the optimized code like a teacher",
  "time_complexity": "Big-O time complexity",
  "space_complexity": "Big-O space complexity",
  "test_cases": [
    {{
      "input": "sample input",
      "expected_output": "sample expected output",
      "actual_output": "actual output or predicted output",
      "status": "Passed or Failed or Not Executed"
    }}
  ]
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        result = extract_json(response.text)

        if not result:
            return {
                "score": 6,
                "feedback": "Gemini evaluated the answer, but response JSON was not perfect.",
                "optimized_approach": "Review the correct DSA pattern and edge cases.",
                "optimized_code": "Could not parse optimized code.",
                "explanation": "Could not parse explanation.",
                "time_complexity": "N/A",
                "space_complexity": "N/A",
                "test_cases": [
                    {
                        "input": "AI evaluation",
                        "expected_output": "Valid JSON",
                        "actual_output": "Invalid Gemini response format",
                        "status": "Not Executed",
                    }
                ],
            }

        result.setdefault("score", 6)
        result.setdefault("feedback", "Your solution was evaluated by Gemini.")
        result.setdefault("optimized_approach", "Use the correct DSA pattern and handle edge cases.")
        result.setdefault("optimized_code", "Optimized code not available.")
        result.setdefault("explanation", "Explanation not available.")
        result.setdefault("time_complexity", "N/A")
        result.setdefault("space_complexity", "N/A")
        result.setdefault("test_cases", [])

        return result

    except Exception:
        return {
            "score": 6,
            "feedback": "Gemini API failed while evaluating this DSA solution.",
            "optimized_approach": "Use the correct DSA pattern and verify edge cases.",
            "optimized_code": "Gemini optimized code unavailable.",
            "explanation": "Gemini explanation unavailable.",
            "time_complexity": "N/A",
            "space_complexity": "N/A",
            "test_cases": [
                {
                    "input": "AI evaluation",
                    "expected_output": "Gemini response",
                    "actual_output": "Gemini API error",
                    "status": "Not Executed",
                }
            ],
        }


def get_fallback_dsa_problem(topic, difficulty):
    topic_key = get_topic_key(topic)

    problems = {
        "arrays": f"""
Problem: Two Sum

Difficulty: {difficulty}
Topic: Arrays

Given an array of integers nums and an integer target, return the indices of the two numbers such that they add up to target.

You may assume that each input has exactly one solution, and you may not use the same element twice.

Input Format:
- nums: List[int]
- target: int

Output Format:
- Return List[int] containing two indices.

Example:
Input:
nums = [2, 7, 11, 15]
target = 9

Output:
[0, 1]

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

Input Format:
- s: str

Output Format:
- Return True if cleaned string is palindrome, otherwise False.

Example:
Input:
s = "A man, a plan, a canal: Panama"

Output:
True

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

A string is valid if:
- Open brackets are closed by the same type of brackets.
- Open brackets are closed in the correct order.

Input Format:
- s: str

Output Format:
- Return True if valid, otherwise False.

Example:
Input:
s = "()[]{{}}"

Output:
True

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

Input Format:
- nums: List[int]
- target: int

Output Format:
- Return int index.

Example:
Input:
nums = [1, 3, 5, 6]
target = 5

Output:
2

Expected Function:
class Solution:
    def searchInsert(self, nums, target):
        pass
""",

        "dynamic programming": f"""
Problem: Climbing Stairs

Difficulty: {difficulty}
Topic: Dynamic Programming

You are climbing a staircase. It takes n steps to reach the top. Each time you can climb either 1 step or 2 steps.

Return the number of distinct ways to climb to the top.

Input Format:
- n: int

Output Format:
- Return number of distinct ways.

Example:
Input:
n = 5

Output:
8

Expected Function:
class Solution:
    def climbStairs(self, n):
        pass
""",

        "linked list": f"""
Problem: Reverse Linked List

Difficulty: {difficulty}
Topic: Linked List

Given the head of a singly linked list, reverse the list and return the new head.

Note:
Real test runner for Linked List will be added later.

Expected Function:
class Solution:
    def reverseList(self, head):
        pass
""",

        "queue": f"""
Problem: Implement Queue using Two Stacks

Difficulty: {difficulty}
Topic: Queue

Implement a queue using two stacks. The queue should support push, pop, peek, and empty operations.

Note:
Real test runner for Queue will be added later.

Expected Class:
class MyQueue:
    def __init__(self):
        pass

    def push(self, x):
        pass

    def pop(self):
        pass

    def peek(self):
        pass

    def empty(self):
        pass
""",

        "trees": f"""
Problem: Maximum Depth of Binary Tree

Difficulty: {difficulty}
Topic: Trees

Given the root of a binary tree, return its maximum depth.

Note:
Real test runner for Trees will be added later.

Expected Function:
class Solution:
    def maxDepth(self, root):
        pass
""",

        "graphs": f"""
Problem: BFS Traversal of Graph

Difficulty: {difficulty}
Topic: Graphs

Given an undirected graph represented using an adjacency list, return BFS traversal from node 0.

Note:
Real test runner for Graphs will be added later.

Expected Function:
class Solution:
    def bfsOfGraph(self, V, adj):
        pass
"""
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
"""
    )


def get_test_cases(topic):
    topic_key = get_topic_key(topic)

    if topic_key == "arrays":
        return [
            {
                "display_input": "nums = [2, 7, 11, 15], target = 9",
                "expected_output": "[0, 1]",
                "nums": [2, 7, 11, 15],
                "target": 9,
                "expected": [0, 1],
            },
            {
                "display_input": "nums = [3, 2, 4], target = 6",
                "expected_output": "[1, 2]",
                "nums": [3, 2, 4],
                "target": 6,
                "expected": [1, 2],
            },
            {
                "display_input": "nums = [3, 3], target = 6",
                "expected_output": "[0, 1]",
                "nums": [3, 3],
                "target": 6,
                "expected": [0, 1],
            },
        ]

    if topic_key == "strings":
        return [
            {
                "display_input": 's = "A man, a plan, a canal: Panama"',
                "expected_output": "True",
                "s": "A man, a plan, a canal: Panama",
                "expected": True,
            },
            {
                "display_input": 's = "race a car"',
                "expected_output": "False",
                "s": "race a car",
                "expected": False,
            },
            {
                "display_input": 's = " "',
                "expected_output": "True",
                "s": " ",
                "expected": True,
            },
        ]

    if topic_key == "stack":
        return [
            {
                "display_input": 's = "()[]{}"',
                "expected_output": "True",
                "s": "()[]{}",
                "expected": True,
            },
            {
                "display_input": 's = "(]"',
                "expected_output": "False",
                "s": "(]",
                "expected": False,
            },
            {
                "display_input": 's = "([{}])"',
                "expected_output": "True",
                "s": "([{}])",
                "expected": True,
            },
        ]

    if topic_key == "binary search":
        return [
            {
                "display_input": "nums = [1, 3, 5, 6], target = 5",
                "expected_output": "2",
                "nums": [1, 3, 5, 6],
                "target": 5,
                "expected": 2,
            },
            {
                "display_input": "nums = [1, 3, 5, 6], target = 2",
                "expected_output": "1",
                "nums": [1, 3, 5, 6],
                "target": 2,
                "expected": 1,
            },
            {
                "display_input": "nums = [1, 3, 5, 6], target = 7",
                "expected_output": "4",
                "nums": [1, 3, 5, 6],
                "target": 7,
                "expected": 4,
            },
        ]

    if topic_key == "dynamic programming":
        return [
            {
                "display_input": "n = 2",
                "expected_output": "2",
                "n": 2,
                "expected": 2,
            },
            {
                "display_input": "n = 3",
                "expected_output": "3",
                "n": 3,
                "expected": 3,
            },
            {
                "display_input": "n = 5",
                "expected_output": "8",
                "n": 5,
                "expected": 8,
            },
        ]

    return []


def run_python_tests(topic, solution):
    if not ENABLE_CODE_EXECUTION:
        return {
            "supported": False,
            "all_passed": False,
            "test_cases": [
                {
                    "input": "Production security mode",
                    "expected_output": "Code execution disabled",
                    "actual_output": "Direct user-code execution is disabled for safety. AI review is used instead.",
                    "status": "Not Executed",
                }
            ],
        }

    topic_key = get_topic_key(topic)

    supported_topics = [
        "arrays",
        "strings",
        "stack",
        "binary search",
        "dynamic programming",
    ]

    if topic_key not in supported_topics:
        return {
            "supported": False,
            "all_passed": False,
            "test_cases": [
                {
                    "input": "Runner not available for this topic yet.",
                    "expected_output": "N/A",
                    "actual_output": "N/A",
                    "status": "Not Executed",
                }
            ],
        }

    tests = get_test_cases(topic)

    payload = {
        "topic_key": topic_key,
        "solution": solution,
        "tests": tests,
    }

    # NOTE: earlier the payload was dumped directly into the f-string,
    # which meant JSON's true/false ended up as bare words in the generated
    # Python code and caused a NameError. Now the JSON is passed in as a
    # string and parsed with json.loads inside the runner instead.
    payload_json = json.dumps(payload)

    runner_code = f"""
import json

payload = json.loads({json.dumps(payload_json)})
topic_key = payload["topic_key"]
user_code = payload["solution"]
tests = payload["tests"]

results = []

try:
    namespace = {{}}
    exec(user_code, namespace)

    Solution = namespace.get("Solution")

    if Solution is None:
        raise Exception("Class Solution not found. Please define class Solution exactly like LeetCode.")

    solver = Solution()

    for test in tests:
        try:
            if topic_key == "arrays":
                actual = solver.twoSum(test["nums"], test["target"])
                passed = sorted(actual) == sorted(test["expected"])

            elif topic_key == "strings":
                actual = solver.isPalindrome(test["s"])
                passed = actual == test["expected"]

            elif topic_key == "stack":
                actual = solver.isValid(test["s"])
                passed = actual == test["expected"]

            elif topic_key == "binary search":
                actual = solver.searchInsert(test["nums"], test["target"])
                passed = actual == test["expected"]

            elif topic_key == "dynamic programming":
                actual = solver.climbStairs(test["n"])
                passed = actual == test["expected"]

            else:
                actual = "N/A"
                passed = False

            results.append({{
                "input": test["display_input"],
                "expected_output": test["expected_output"],
                "actual_output": repr(actual),
                "status": "Passed" if passed else "Failed"
            }})

        except Exception as e:
            results.append({{
                "input": test["display_input"],
                "expected_output": test["expected_output"],
                "actual_output": "Runtime Error: " + str(e),
                "status": "Failed"
            }})

    print(json.dumps({{
        "results": results,
        "all_passed": all(item["status"] == "Passed" for item in results)
    }}))

except Exception as e:
    print(json.dumps({{
        "results": [
            {{
                "input": "Code setup",
                "expected_output": "Executable LeetCode-style Solution class",
                "actual_output": "Error: " + str(e),
                "status": "Failed"
            }}
        ],
        "all_passed": False
    }}))
"""

    temp_file_path = ""

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        ) as temp_file:
            temp_file.write(runner_code)
            temp_file_path = temp_file.name

        completed = subprocess.run(
            [sys.executable, temp_file_path],
            capture_output=True,
            text=True,
            timeout=3
        )

        output = completed.stdout.strip()

        if not output:
            return {
                "supported": True,
                "all_passed": False,
                "test_cases": [
                    {
                        "input": "Code execution",
                        "expected_output": "Valid output",
                        "actual_output": completed.stderr.strip() or "No output",
                        "status": "Failed",
                    }
                ],
            }

        parsed = json.loads(output)

        return {
            "supported": True,
            "all_passed": parsed.get("all_passed", False),
            "test_cases": parsed.get("results", []),
        }

    except subprocess.TimeoutExpired:
        return {
            "supported": True,
            "all_passed": False,
            "test_cases": [
                {
                    "input": "All test cases",
                    "expected_output": "Code should finish within time limit",
                    "actual_output": "Time Limit Exceeded",
                    "status": "Failed",
                }
            ],
        }

    except Exception as e:
        return {
            "supported": True,
            "all_passed": False,
            "test_cases": [
                {
                    "input": "Code execution",
                    "expected_output": "Valid Python execution",
                    "actual_output": "Error: " + str(e),
                    "status": "Failed",
                }
            ],
        }

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass


def get_optimized_solution(topic):
    topic_key = get_topic_key(topic)

    if topic_key == "arrays":
        return {
            "optimized_approach": "Use a hash map to store previously visited numbers with their indices. For each number, calculate complement = target - num. If complement exists in the map, return the stored index and current index.",
            "optimized_code": """class Solution:
    def twoSum(self, nums, target):
        seen = {}

        for i, num in enumerate(nums):
            complement = target - num

            if complement in seen:
                return [seen[complement], i]

            seen[num] = i

        return []""",
            "explanation": "We traverse the array once. For every number, we check whether the number needed to complete the target already appeared before. If yes, we return both indices. This avoids checking every pair.",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
        }

    if topic_key == "strings":
        return {
            "optimized_approach": "Use two pointers. Move left forward if it is not alphanumeric, move right backward if it is not alphanumeric. Compare lowercase characters.",
            "optimized_code": """class Solution:
    def isPalindrome(self, s):
        left = 0
        right = len(s) - 1

        while left < right:
            while left < right and not s[left].isalnum():
                left += 1

            while left < right and not s[right].isalnum():
                right -= 1

            if s[left].lower() != s[right].lower():
                return False

            left += 1
            right -= 1

        return True""",
            "explanation": "The two-pointer approach compares valid characters from both ends and ignores spaces, commas, and symbols. This avoids building a separate cleaned string.",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
        }

    if topic_key == "stack":
        return {
            "optimized_approach": "Use a stack and a bracket map. When a closing bracket appears, check whether stack top matches the required opening bracket.",
            "optimized_code": """class Solution:
    def isValid(self, s):
        stack = []
        pairs = {
            ')': '(',
            '}': '{',
            ']': '['
        }

        for char in s:
            if char in pairs.values():
                stack.append(char)
            else:
                if not stack or stack[-1] != pairs[char]:
                    return False
                stack.pop()

        return len(stack) == 0""",
            "explanation": "The stack stores the latest unmatched opening bracket. Every closing bracket must match the top of the stack.",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
        }

    if topic_key == "binary search":
        return {
            "optimized_approach": "Use binary search to find the first position where nums[index] is greater than or equal to target.",
            "optimized_code": """class Solution:
    def searchInsert(self, nums, target):
        left = 0
        right = len(nums)

        while left < right:
            mid = (left + right) // 2

            if nums[mid] < target:
                left = mid + 1
            else:
                right = mid

        return left""",
            "explanation": "Binary search repeatedly removes half of the search space. At the end, left points to the correct index where target exists or should be inserted.",
            "time_complexity": "O(log n)",
            "space_complexity": "O(1)",
        }

    if topic_key == "dynamic programming":
        return {
            "optimized_approach": "Use two variables to store previous two states instead of a full DP array.",
            "optimized_code": """class Solution:
    def climbStairs(self, n):
        if n <= 2:
            return n

        first = 1
        second = 2

        for step in range(3, n + 1):
            current = first + second
            first = second
            second = current

        return second""",
            "explanation": "The number of ways to reach step n is ways(n-1) + ways(n-2). We only need the previous two values, so space can be optimized.",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
        }

    return {
        "optimized_approach": "Identify the correct DSA pattern, handle edge cases, and write clean code.",
        "optimized_code": """class Solution:
    def solve(self):
        pass""",
        "explanation": "Optimized explanation will be added for this topic later.",
        "time_complexity": "Depends on selected problem",
        "space_complexity": "Depends on selected problem",
    }


def fallback_dsa_evaluation(topic, solution, runner_result=None):
    optimized = get_optimized_solution(topic)

    if runner_result and runner_result.get("supported"):
        all_passed = runner_result.get("all_passed", False)
        test_cases = runner_result.get("test_cases", [])

        if all_passed:
            score = 10
            feedback = "Your code passed all predefined test cases. The logic is correct for this supported problem."
        else:
            score = 5
            feedback = "Your code did not pass all predefined test cases. Check the failed cases, fix the logic, and try again."

        return {
            "score": score,
            "feedback": feedback,
            "optimized_approach": optimized["optimized_approach"],
            "optimized_code": optimized["optimized_code"],
            "explanation": optimized["explanation"],
            "time_complexity": optimized["time_complexity"],
            "space_complexity": optimized["space_complexity"],
            "test_cases": test_cases,
        }

    return {
        "score": 6,
        "feedback": "Your solution was received. Real runner is not available for this topic yet, so this is fallback feedback.",
        "optimized_approach": optimized["optimized_approach"],
        "optimized_code": optimized["optimized_code"],
        "explanation": optimized["explanation"],
        "time_complexity": optimized["time_complexity"],
        "space_complexity": optimized["space_complexity"],
        "test_cases": [
            {
                "input": "Runner not available for this topic yet.",
                "expected_output": "N/A",
                "actual_output": "N/A",
                "status": "Not Executed",
            }
        ],
    }


@app.get("/")
def home():
    return {
        "message": "ConceptVivaAI Python FastAPI backend is running"
    }


@app.get("/dsa-question-bank")
def dsa_question_bank():
    return {
        "total": len(DSA_QUESTION_BANK),
        "questions": get_all_dsa_questions(),
    }


@app.get("/dsa-question-bank/stats")
def dsa_question_bank_stats():
    return {
        "total": len(DSA_QUESTION_BANK),
        "easy": len(get_dsa_questions_by_difficulty("Easy")),
        "medium": len(get_dsa_questions_by_difficulty("Medium")),
        "hard": len(get_dsa_questions_by_difficulty("Hard")),
    }


@app.post("/generate-dsa-mock-set")
def generate_dsa_mock_set(
    request: DSAMockSetRequest,
    session_id: str = Depends(get_current_session_id),
):
    questions = get_dsa_mock_set(
        topic=request.topic,
        difficulty=request.difficulty,
        count=request.count
    )

    return {
        "mode": "mock_set",
        "topic": request.topic,
        "difficulty": request.difficulty,
        "count": len(questions),
        "distribution": get_difficulty_distribution(questions),
        "questions": questions,
        "message": "Mock set generated successfully. Mixed mode follows 3 Easy + 4 Medium + 3 Hard when enough questions are available.",
    }


@app.post("/generate-dsa-practice-question")
def generate_dsa_practice_question(
    request: DSAPracticeQuestionRequest,
    session_id: str = Depends(get_current_session_id),
):
    question = get_dsa_practice_question(
        topic=request.topic,
        difficulty=request.difficulty
    )

    if not question:
        return {
            "mode": "practice",
            "question": None,
            "problem": get_fallback_dsa_problem(request.topic, request.difficulty),
            "problem_json": None,
            "starter_code": get_default_starter_code(),
            "message": "No matching question found in DSA bank. Fallback problem returned.",
        }

    problem_json = generate_dsa_problem_json_from_gemini(question)
    problem_text = build_problem_text_from_json(problem_json)

    return {
        "mode": "practice",
        "question": question,
        "problem": problem_text,
        "problem_json": problem_json,
        "starter_code": problem_json.get("starter_code", get_default_starter_code()),
        "message": "Practice question generated successfully.",
    }


@app.post("/generate-own-dsa-question")
def generate_own_dsa_question(
    request: DSAOwnQuestionRequest,
    session_id: str = Depends(get_current_session_id),
):
    question = {
        "id": "custom_user_question",
        "title": request.title,
        "topic": request.topic,
        "difficulty": request.difficulty,
        "pattern": request.pattern,
        "source": "User Provided",
    }

    problem_json = generate_dsa_problem_json_from_gemini(question)
    problem_text = build_problem_text_from_json(problem_json)

    return {
        "mode": "own_question",
        "question": question,
        "problem": problem_text,
        "problem_json": problem_json,
        "starter_code": problem_json.get("starter_code", get_default_starter_code()),
        "message": "Own question converted into practice problem successfully.",
    }


@app.post("/generate-question")
def generate_question(
    request: QuestionRequest,
    session_id: str = Depends(get_current_session_id),
):
    if not GEMINI_API_KEY or not client:
        return {
            "question": f"Can you explain the basic concept of {request.topic}?"
        }

    prompt = f"""
You are ConceptVivaAI, a strict real interview agent.

Generate only one interview question.

Topic: {request.topic}
Difficulty: {request.level}

Rules:
- Ask only one question.
- Stay strictly inside the selected topic.
- Do not provide the answer.
- Question should sound like a real interviewer.
- Keep it clear and natural.
- Prefer conceptual, practical, and interview-relevant questions.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return {
            "question": response.text
        }

    except Exception:
        return {
            "question": f"Can you explain the basic concept of {request.topic} and why it is important?"
        }


@app.post("/evaluate-answer")
def evaluate_answer(
    request: EvaluateRequest,
    session_id: str = Depends(get_current_session_id),
):
    if not GEMINI_API_KEY or not client:
        return {
            "score": 5,
            "feedback": "Your answer was received. Since AI quota is unavailable right now, this is a fallback evaluation.",
            "improvement": "Structure your answer with definition, working, example, and limitation.",
            "follow_up_question": f"Can you give one real-world example of {request.topic}?"
        }

    prompt = f"""
You are ConceptVivaAI, a strict but fair semantic mock interview evaluator.

Your job:
Evaluate the student's answer based on meaning, concept correctness, and interview quality.

Topic:
{request.topic}

Difficulty:
{request.level}

Interviewer Question:
{request.question}

Student Answer:
{request.answer}

Very important evaluation rules:
1. Do NOT compare the student's answer word-by-word with an ideal answer.
2. Accept different wording if the meaning and concept are correct.
3. Evaluate semantic correctness, not exact sentence matching.
4. Penalize wrong meaning, wrong tense, wrong technical claim, or contradiction.
5. Penalize vague answers that sound related but do not actually answer the question.
6. Check whether important keywords/concepts are present.
7. Check if the answer is interview-ready, structured, and clear.
8. If the student uses simple English but the concept is correct, give a good score.
9. If the student uses fancy English but the concept is wrong, give a low score.
10. Stay strictly inside the selected topic.

Example of semantic evaluation:
- "Linear Regression predicts continuous values" and
  "It estimates numeric output from input features" are semantically similar and should be accepted.
- "Linear Regression is used for classification" is technically wrong and should be penalized.
- "I went", "I am going", and "I will go" are not the same meaning because tense changes the meaning.

Scoring guide:
0-2: Completely wrong or unrelated.
3-4: Some related words, but concept is mostly wrong.
5-6: Basic idea present, but incomplete or vague.
7-8: Correct answer with minor missing points.
9-10: Strong, structured, interview-ready answer with example or depth.

Return only valid JSON in this exact format:
{{
  "score": number from 0 to 10,
  "verdict": "STRONG or PARTIAL or WEAK",
  "feedback": "Explain what was correct and what was wrong. Mention that alternative wording is accepted if meaning is correct.",
  "missing_points": "Important points missing from the student's answer.",
  "corrected_answer": "A better interview-ready answer in simple English.",
  "improvement": "One specific improvement tip for the student.",
  "follow_up_question": "One follow-up interview question based on the student's answer"
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        result = extract_json(response.text)

        if not result:
            return {
                "score": 5,
                "verdict": "PARTIAL",
                "feedback": "AI evaluated the answer, but response format was not perfect.",
                "missing_points": "Answer needs more clarity and important topic keywords.",
                "corrected_answer": "Give the answer using definition, working, example, and limitation.",
                "improvement": "Give answer in a structured way: definition, working, example, limitation.",
                "follow_up_question": "Can you explain this concept with one real-world example?"
            }

        if "score" not in result:
            result["score"] = 5

        if "verdict" not in result:
            result["verdict"] = "PARTIAL"

        if "feedback" not in result:
            result["feedback"] = "Your answer was evaluated based on semantic meaning, not exact wording."

        if "missing_points" not in result:
            result["missing_points"] = "Mention key concepts, working, and example."

        if "corrected_answer" not in result:
            result["corrected_answer"] = "A strong answer should include definition, working, example, and limitation."

        if "improvement" not in result:
            result["improvement"] = "Improve structure and add one practical example."

        if "follow_up_question" not in result:
            result["follow_up_question"] = f"Can you explain one practical use case of {request.topic}?"

        return result

    except Exception:
        return {
            "score": 5,
            "verdict": "PARTIAL",
            "feedback": "Your answer was received, but Gemini quota/API is currently unavailable.",
            "missing_points": "Could not check detailed semantic correctness right now.",
            "corrected_answer": "A strong answer should include definition, working, example, and limitation.",
            "improvement": "Improve by adding definition, working, example, and limitation.",
            "follow_up_question": f"Can you explain one practical use case of {request.topic}?"
        }


@app.post("/generate-dsa-problem")
def generate_dsa_problem(
    request: DSAProblemRequest,
    session_id: str = Depends(get_current_session_id),
):
    question = get_dsa_practice_question(
        topic=request.topic,
        difficulty=request.difficulty
    )

    if not question:
        return {
            "problem": get_fallback_dsa_problem(request.topic, request.difficulty),
            "problem_json": None,
            "starter_code": get_default_starter_code(),
            "question": None,
            "message": "No matching question found in new DSA bank. Fallback problem returned.",
        }

    problem_json = generate_dsa_problem_json_from_gemini(question)
    problem_text = build_problem_text_from_json(problem_json)

    return {
        "problem": problem_text,
        "problem_json": problem_json,
        "starter_code": problem_json.get("starter_code", get_default_starter_code()),
        "question": question,
        "message": "DSA problem generated from curated question bank.",
    }


@app.post("/evaluate-dsa-solution")
def evaluate_dsa_solution(
    request: DSAEvaluateRequest,
    session_id: str = Depends(get_current_session_id),
):
    question_id = extract_question_id_from_problem_text(request.problem)

    if question_id:
        question = get_dsa_question_by_id(question_id)

        if question:
            return evaluate_bank_dsa_solution_with_gemini(
                question=question,
                problem_text=request.problem,
                solution=request.solution
            )

    runner_result = run_python_tests(request.topic, request.solution)

    if runner_result.get("supported"):
        return fallback_dsa_evaluation(
            request.topic,
            request.solution,
            runner_result
        )

    if not GEMINI_API_KEY or not client:
        return fallback_dsa_evaluation(request.topic, request.solution, runner_result)

    prompt = f"""
You are ConceptVivaAI, a strict DSA solution evaluator.

Evaluate the user's approach or code.

DSA Topic: {request.topic}
Difficulty: {request.difficulty}

Problem:
{request.problem}

User Solution or Approach:
{request.solution}

Return only valid JSON in this exact format:
{{
  "score": number from 0 to 10,
  "feedback": "clear feedback about correctness, logic, and missing cases",
  "optimized_approach": "best optimized approach explained clearly",
  "optimized_code": "complete optimized Python code",
  "explanation": "explain the optimized code like a teacher",
  "time_complexity": "Big-O time complexity",
  "space_complexity": "Big-O space complexity",
  "test_cases": [
    {{
      "input": "sample input",
      "expected_output": "sample expected output",
      "actual_output": "actual output",
      "status": "Passed or Failed or Not Executed"
    }}
  ]
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        result = extract_json(response.text)

        if not result:
            return fallback_dsa_evaluation(request.topic, request.solution, runner_result)

        optimized = get_optimized_solution(request.topic)

        if "test_cases" not in result:
            result["test_cases"] = runner_result.get("test_cases", [])

        if "optimized_code" not in result:
            result["optimized_code"] = optimized["optimized_code"]

        if "explanation" not in result:
            result["explanation"] = optimized["explanation"]

        return result

    except Exception:
        return fallback_dsa_evaluation(request.topic, request.solution, runner_result)


class ProjectChallengeRequest(BaseModel):
    domain: str = "Machine Learning"
    topic: str = "AI Selected Topic"
    difficulty: str = "Beginner"


class ProjectSubmissionRequest(BaseModel):
    challenge_id: str
    submission: str


def get_fallback_project_challenge(domain, topic, difficulty):
    return {
        "project_title": f"{topic} Mini Project Challenge",
        "domain": domain,
        "topic": topic,
        "difficulty": difficulty,
        "problem_statement": (
            f"Build a beginner-friendly project using {topic}. "
            "Your goal is to understand the concept, apply it on a simple dataset, "
            "evaluate the result, and explain your approach clearly."
        ),
        "dataset_columns": [
            {"column": "feature_1", "description": "First input feature"},
            {"column": "feature_2", "description": "Second input feature"},
            {"column": "target", "description": "Output variable to predict or analyze"},
        ],
        "tasks": [
            "Understand the problem statement.",
            "Create or load a small dataset.",
            "Clean the data and handle missing values.",
            f"Apply {topic} correctly.",
            "Evaluate the output using suitable metrics.",
            "Write a short explanation of your approach and result.",
        ],
        "evaluation_metrics": [
            "Correct use of selected concept",
            "Data preprocessing quality",
            "Model or solution logic",
            "Evaluation and interpretation",
            "Clarity of explanation",
        ],
        "hints": [
            "Start with a very small dataset.",
            "Explain every step in simple words.",
            "Mention why this concept is suitable for the problem.",
        ],
        "submission_checklist": [
            "Problem understanding",
            "Dataset columns",
            "Approach or code",
            "Output/result",
            "Evaluation metric",
            "Conclusion",
        ],
    }


def generate_project_challenge_with_gemini(domain, topic, difficulty):
    if not GEMINI_API_KEY or not client:
        return get_fallback_project_challenge(domain, topic, difficulty)

    prompt = f"""
You are ConceptVivaAI, an AI assessment platform.

Generate a project-based challenge for a student.

Domain: {domain}
Topic: {topic}
Difficulty: {difficulty}

The challenge should be practical, beginner-friendly if difficulty is Beginner,
and should feel like a mini hackathon/project assignment.

Return only valid JSON in this exact format:
{{
  "project_title": "clear project title",
  "domain": "{domain}",
  "topic": "{topic}",
  "difficulty": "{difficulty}",
  "problem_statement": "detailed but simple problem statement",
  "dataset_columns": [
    {{
      "column": "column_name",
      "description": "what this column means"
    }}
  ],
  "tasks": [
    "task 1",
    "task 2",
    "task 3"
  ],
  "evaluation_metrics": [
    "metric or evaluation point 1",
    "metric or evaluation point 2"
  ],
  "hints": [
    "hint 1",
    "hint 2"
  ],
  "submission_checklist": [
    "checklist item 1",
    "checklist item 2"
  ]
}}

Rules:
1. Stay strictly inside the selected topic.
2. Do not give the full solution.
3. Do not provide complete code.
4. Give a dataset/table schema.
5. Make it useful for portfolio/project practice.
6. Keep it clear for students.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        result = extract_json(response.text)

        if not result:
            return get_fallback_project_challenge(domain, topic, difficulty)

        result.setdefault("project_title", f"{topic} Mini Project Challenge")
        result.setdefault("domain", domain)
        result.setdefault("topic", topic)
        result.setdefault("difficulty", difficulty)
        result.setdefault("problem_statement", "Project problem statement not available.")
        result.setdefault("dataset_columns", [])
        result.setdefault("tasks", [])
        result.setdefault("evaluation_metrics", [])
        result.setdefault("hints", [])
        result.setdefault("submission_checklist", [])

        return result

    except Exception:
        return get_fallback_project_challenge(domain, topic, difficulty)


def evaluate_project_submission_with_gemini(
    domain,
    topic,
    difficulty,
    challenge,
    submission
):
    if not GEMINI_API_KEY or not client:
        return {
            "score": 6,
            "verdict": "PARTIAL",
            "feedback": "Your project submission was received. Gemini API is unavailable right now, so this is fallback feedback.",
            "missing_points": "Detailed AI review could not run. Make sure your submission includes dataset, preprocessing, approach, evaluation, and conclusion.",
            "improved_approach": "Use a clear structure: problem understanding, dataset columns, preprocessing, model/logic, evaluation metric, result interpretation, and conclusion.",
            "next_steps": "Add code, evaluate results, explain limitations, and improve the project for portfolio use.",
            "suggested_resources": [
                "Revise the selected concept",
                "Practice one small dataset-based implementation",
                "Write a short project report"
            ],
        }

    prompt = f"""
You are ConceptVivaAI, a strict but helpful project evaluator.

Evaluate the student's project submission.

Domain:
{domain}

Topic:
{topic}

Difficulty:
{difficulty}

Project Challenge:
{json.dumps(challenge, indent=2)}

Student Submission:
{submission}

Evaluate:
1. Whether the student understood the problem.
2. Whether the approach is correct for the selected topic.
3. Whether dataset/table understanding is present.
4. Whether preprocessing/model/evaluation steps are clear.
5. Whether the explanation is portfolio-ready.
6. Missing technical points.
7. Give an improved project approach.

Return only valid JSON in this exact format:
{{
  "score": number from 0 to 10,
  "verdict": "STRONG or PARTIAL or WEAK",
  "feedback": "clear feedback about what is correct and incorrect",
  "missing_points": "important missing points",
  "improved_approach": "better project approach in simple steps",
  "next_steps": "what student should do next",
  "suggested_resources": [
    "resource or topic 1",
    "resource or topic 2"
  ]
}}

Scoring guide:
0-2: unrelated or empty submission.
3-4: weak understanding with very little correct structure.
5-6: basic idea present but incomplete.
7-8: good project approach with minor missing points.
9-10: strong, clear, portfolio-ready project approach.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        result = extract_json(response.text)

        if not result:
            return {
                "score": 6,
                "verdict": "PARTIAL",
                "feedback": "AI reviewed the project, but response JSON was not perfect.",
                "missing_points": "Add more structure, metrics, dataset explanation, and conclusion.",
                "improved_approach": "Explain the problem, dataset, preprocessing, model/logic, metric, result, limitation, and improvement.",
                "next_steps": "Improve project explanation and add proper evaluation.",
                "suggested_resources": [
                    "Selected concept revision",
                    "Project report writing",
                    "Model evaluation metrics"
                ],
            }

        result.setdefault("score", 6)
        result.setdefault("verdict", "PARTIAL")
        result.setdefault("feedback", "Your project was evaluated by AI.")
        result.setdefault("missing_points", "Mention dataset, preprocessing, evaluation, and conclusion.")
        result.setdefault("improved_approach", "Use a structured project approach.")
        result.setdefault("next_steps", "Improve your project and resubmit.")
        result.setdefault("suggested_resources", [])

        return result

    except Exception:
        return {
            "score": 6,
            "verdict": "PARTIAL",
            "feedback": "Gemini API failed while evaluating the project submission.",
            "missing_points": "Could not check detailed missing points right now.",
            "improved_approach": "Use a clear structure: problem, dataset, preprocessing, approach, evaluation, result, conclusion.",
            "next_steps": "Try again after backend/Gemini is available.",
            "suggested_resources": [
                "Concept revision",
                "Project-based ML practice",
                "Evaluation metrics"
            ],
        }


@app.post("/generate-project-challenge")
def generate_project_challenge(
    request: ProjectChallengeRequest,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db)
):
    challenge = generate_project_challenge_with_gemini(
        domain=request.domain,
        topic=request.topic,
        difficulty=request.difficulty
    )

    stored_challenge = create_project_challenge(
        db,
        {
            "session_id": session_id,
            "domain": request.domain,
            "topic": request.topic,
            "difficulty": request.difficulty,
            "project_title": challenge.get("project_title", "Project Challenge"),
            "challenge": challenge,
        }
    )

    return {
        "mode": "project_challenge",
        "challenge_id": stored_challenge.challenge_id,
        "challenge": challenge,
        "message": "Project challenge generated and stored successfully.",
    }


@app.post("/evaluate-project-submission")
def evaluate_project_submission(
    request: ProjectSubmissionRequest,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db)
):
    stored_challenge = get_project_challenge_by_id(
        db,
        session_id=session_id,
        challenge_id=request.challenge_id
    )

    if not stored_challenge:
        raise HTTPException(
            status_code=404,
            detail="Project challenge not found for this session."
        )

    challenge = decode_project_challenge(stored_challenge.challenge_json)

    review = evaluate_project_submission_with_gemini(
        domain=stored_challenge.domain,
        topic=stored_challenge.topic,
        difficulty=stored_challenge.difficulty,
        challenge=challenge,
        submission=request.submission
    )

    return {
        **review,
        "challenge_id": stored_challenge.challenge_id,
        "verified_challenge": True,
    }


@app.post("/save-ml-practice-attempt")
def save_ml_practice_attempt(
    request: SaveMLPracticeAttemptRequest,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db)
):
    attempt = create_ml_practice_attempt(
        db,
        {
            "session_id": session_id,
            "topic": request.topic,
            "level": request.level,
            "question": request.question,
            "answer": request.answer,
            "score": request.score,
            "verdict": request.verdict,
            "feedback": request.feedback,
            "missing_points": request.missing_points,
            "corrected_answer": request.corrected_answer,
            "improvement": request.improvement,
        }
    )

    return {
        "message": "ML practice attempt saved successfully.",
        "attempt": serialize_ml_attempt(attempt),
    }


@app.post("/save-interview-report")
def save_interview_report(
    request: SaveInterviewReportRequest,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db)
):
    report = create_interview_report(
        db,
        {
            "session_id": session_id,
            "topic": request.topic,
            "level": request.level,
            "rounds": request.rounds,
            "average_score": request.average_score,
            "strong_points": request.strong_points,
            "weak_points": request.weak_points,
            "recommendation": request.recommendation,
        }
    )

    return {
        "message": "Interview report saved successfully.",
        "report": serialize_interview_report(report),
    }


@app.post("/save-dsa-attempt")
def save_dsa_attempt(
    request: SaveDSAAttemptRequest,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db)
):
    attempt = create_dsa_attempt(
        db,
        {
            "session_id": session_id,
            "mode": request.mode,
            "topic": request.topic,
            "difficulty": request.difficulty,
            "problem_name": request.problem_name,
            "problem": request.problem,
            "solution": request.solution,
            "score": request.score,
            "status": request.status,
            "feedback": request.feedback,
        }
    )

    return {
        "message": "DSA attempt saved successfully.",
        "attempt": serialize_dsa_attempt(attempt),
    }


@app.post("/save-project-attempt")
def save_project_attempt(
    request: SaveProjectAttemptRequest,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db)
):
    challenge = request.challenge
    domain = request.domain
    topic = request.topic
    difficulty = request.difficulty
    project_title = request.project_title

    if request.challenge_id:
        stored_challenge = get_project_challenge_by_id(
            db,
            session_id=session_id,
            challenge_id=request.challenge_id
        )

        if not stored_challenge:
            raise HTTPException(
                status_code=404,
                detail="Project challenge not found for this session."
            )

        challenge = decode_project_challenge(stored_challenge.challenge_json)
        domain = stored_challenge.domain
        topic = stored_challenge.topic
        difficulty = stored_challenge.difficulty
        project_title = stored_challenge.project_title

    attempt = create_project_attempt(
        db,
        {
            "session_id": session_id,
            "challenge_id": request.challenge_id,
            "domain": domain,
            "topic": topic,
            "difficulty": difficulty,
            "project_title": project_title,
            "challenge": challenge,
            "submission": request.submission,
            "score": request.score,
            "verdict": request.verdict,
            "feedback": request.feedback,
            "missing_points": request.missing_points,
            "improved_approach": request.improved_approach,
            "next_steps": request.next_steps,
        }
    )

    # once the attempt is saved, mark the challenge as completed,
    # otherwise the dashboard's active challenge count keeps growing forever
    if request.challenge_id:
        mark_project_challenge_completed(
            db,
            session_id=session_id,
            challenge_id=request.challenge_id,
        )

    return {
        "message": "Project attempt saved successfully.",
        "verified_challenge": bool(request.challenge_id),
        "attempt": serialize_project_attempt(attempt),
    }


@app.get("/dashboard-stats")
def dashboard_stats(
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db)
):
    return get_dashboard_stats(db, session_id)


@app.get("/history")
def history(
    limit: int = 20,
    offset: int = 0,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db)
):
    history_data = get_user_history(db, session_id, limit=limit, offset=offset)

    return {
        "session_id": session_id,
        "pagination": history_data.get(
            "pagination",
            {
                "limit": limit,
                "offset": offset,
            }
        ),
        "ml_practice": [
            serialize_ml_attempt(item)
            for item in history_data["ml_practice"]
        ],
        "dsa_practice": [
            serialize_dsa_attempt(item)
            for item in history_data["dsa_practice"]
        ],
        "project_challenge": [
            serialize_project_attempt(item)
            for item in history_data["project_challenge"]
        ],
        "voice_interview": [
            serialize_interview_report(item)
            for item in history_data["voice_interview"]
        ],
    }
