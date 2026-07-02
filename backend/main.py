import os
import json
import re
import sys
import tempfile
import subprocess
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai


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


load_dotenv("../.env.local")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

app = FastAPI(title="ConceptVivaAI Backend")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://192.168.29.17:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def build_question_metadata_text(question):
    return f"""
Question ID: {question.get("id", "")}
Question Title: {question.get("title", "")}
Topic: {question.get("topic", "")}
Difficulty: {question.get("difficulty", "")}
Pattern: {question.get("pattern", "")}
Source: {question.get("source", "")}
"""


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


def generate_dsa_problem_from_gemini(question):
    title = question.get("title", "DSA Problem")
    topic = question.get("topic", "DSA")
    difficulty = question.get("difficulty", "Medium")
    pattern = question.get("pattern", "General DSA")
    question_id = question.get("id", "")

    if not GEMINI_API_KEY or not client:
        return f"""
Question ID: {question_id}

Problem: {title}

Topic: {topic}
Difficulty: {difficulty}
Pattern: {pattern}

Generate and solve this problem using the correct DSA pattern.

Important:
- Write a LeetCode-style class Solution.
- Do not change the expected function name once decided.
- Think about edge cases.

Note:
Gemini API is currently unavailable, so this is a fallback problem shell.
"""

    prompt = f"""
You are ConceptVivaAI, a strict DSA practice problem generator.

Generate a coding practice problem for the user.

Question metadata:
Question ID: {question_id}
Title: {title}
Topic: {topic}
Difficulty: {difficulty}
Pattern: {pattern}

Very important rules:
1. Do NOT provide the solution.
2. Do NOT provide optimized code.
3. Do NOT explain the answer.
4. Only provide the problem statement and starter code.
5. The problem should be interview-style and LeetCode/GFG-style.
6. Include input format, output format, constraints, and 2-3 sample test cases.
7. Include one expected Python starter code using class Solution.
8. Keep the function name natural for this problem.
9. Stay strictly aligned with the title, topic, difficulty, and pattern.
10. Do not hallucinate a different problem.

Return the response in clean text format like this:

Question ID: {question_id}

Problem: {title}

Difficulty: {difficulty}
Topic: {topic}
Pattern: {pattern}

Problem Statement:
...

Input Format:
...

Output Format:
...

Constraints:
...

Examples:
...

Starter Code:
class Solution:
    def functionName(self, ...):
        # Write your code here
        pass
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return response.text

    except Exception:
        return f"""
Question ID: {question_id}

Problem: {title}

Topic: {topic}
Difficulty: {difficulty}
Pattern: {pattern}

Problem Statement:
Solve the problem "{title}" using the most suitable DSA technique.

Expected Function:
class Solution:
    def solve(self):
        # Write your code here
        pass

Note:
Gemini API is currently unavailable, so detailed problem generation failed.
"""


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

    runner_code = f"""
import json

payload = {json.dumps(payload)}
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
def generate_dsa_mock_set(request: DSAMockSetRequest):
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
def generate_dsa_practice_question(request: DSAPracticeQuestionRequest):
    question = get_dsa_practice_question(
        topic=request.topic,
        difficulty=request.difficulty
    )

    if not question:
        return {
            "mode": "practice",
            "question": None,
            "problem": get_fallback_dsa_problem(request.topic, request.difficulty),
            "message": "No matching question found in DSA bank. Fallback problem returned.",
        }

    problem_text = generate_dsa_problem_from_gemini(question)

    return {
        "mode": "practice",
        "question": question,
        "problem": problem_text,
        "message": "Practice question generated successfully.",
    }


@app.post("/generate-own-dsa-question")
def generate_own_dsa_question(request: DSAOwnQuestionRequest):
    question = {
        "id": "custom_user_question",
        "title": request.title,
        "topic": request.topic,
        "difficulty": request.difficulty,
        "pattern": request.pattern,
        "source": "User Provided",
    }

    problem_text = generate_dsa_problem_from_gemini(question)

    return {
        "mode": "own_question",
        "question": question,
        "problem": problem_text,
        "message": "Own question converted into practice problem successfully.",
    }


@app.post("/generate-question")
def generate_question(request: QuestionRequest):
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
def evaluate_answer(request: EvaluateRequest):
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
def generate_dsa_problem(request: DSAProblemRequest):
    question = get_dsa_practice_question(
        topic=request.topic,
        difficulty=request.difficulty
    )

    if not question:
        return {
            "problem": get_fallback_dsa_problem(request.topic, request.difficulty),
            "question": None,
            "message": "No matching question found in new DSA bank. Fallback problem returned.",
        }

    problem_text = generate_dsa_problem_from_gemini(question)

    return {
        "problem": problem_text,
        "question": question,
        "message": "DSA problem generated from curated question bank.",
    }


@app.post("/evaluate-dsa-solution")
def evaluate_dsa_solution(request: DSAEvaluateRequest):
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
    topic: str = "Linear Regression"
    difficulty: str = "Beginner"


class ProjectSubmissionRequest(BaseModel):
    domain: str = "Machine Learning"
    topic: str = "Linear Regression"
    difficulty: str = "Beginner"
    challenge: dict
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
def generate_project_challenge(request: ProjectChallengeRequest):
    challenge = generate_project_challenge_with_gemini(
        domain=request.domain,
        topic=request.topic,
        difficulty=request.difficulty
    )

    return {
        "mode": "project_challenge",
        "challenge": challenge,
        "message": "Project challenge generated successfully.",
    }


@app.post("/evaluate-project-submission")
def evaluate_project_submission(request: ProjectSubmissionRequest):
    review = evaluate_project_submission_with_gemini(
        domain=request.domain,
        topic=request.topic,
        difficulty=request.difficulty,
        challenge=request.challenge,
        submission=request.submission
    )

    return review