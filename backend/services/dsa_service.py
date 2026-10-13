"""DSA question generation and evaluation helpers."""
from uuid import uuid4

from config import ENABLE_CODE_EXECUTION, GEMINI_API_KEY
from dsa_runner import run_question_tests
from services.dsa_bank import get_dsa_question_by_title
from services.gemini_client import client
from utils import extract_json, get_topic_key


# verified = hidden-test scored, ai_generated = AI-reviewed only.
TIER_VERIFIED = "verified"
TIER_AI_GENERATED = "ai_generated"


def get_question_tier(runner_supported):
    return TIER_VERIFIED if runner_supported else TIER_AI_GENERATED


def is_hidden_test_available(question):
    """Return True only when this question can use the local runner."""
    return bool(ENABLE_CODE_EXECUTION and question and question.get("runner"))


def generate_ai_practice_question(topic, difficulty, recent_titles=None):
    """Generate a custom-topic problem that will be AI-reviewed."""
    synthetic_question = {
        "id": "",
        "title": f"{topic} Practice Problem",
        "topic": topic,
        "difficulty": difficulty,
        "pattern": "AI Generated",
        "source": "AI Generated",
    }
    problem_json = generate_dsa_problem_json_from_gemini(
        synthetic_question,
        enforce_signature=False,
        recent_titles=recent_titles,
    )
    # Empty id keeps AI-practice questions out of the curated runner path.
    problem_json["question_id"] = ""
    return synthetic_question, problem_json


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
            "Note: Gemini API is currently unavailable, so this is a fallback "
            "problem shell without detailed statement."
        ),
        "examples": [],
        "constraints": [],
        "follow_up": "",
        "starter_code": question.get("starter_code") or get_default_starter_code(),
    }


def generate_dsa_problem_json_from_gemini(question, enforce_signature=True, recent_titles=None):
    """Generate a structured LeetCode-style problem."""
    title = question.get("title", "DSA Problem")
    topic = question.get("topic", "DSA")
    difficulty = question.get("difficulty", "Medium")
    pattern = question.get("pattern", "General DSA")
    question_id = question.get("id", "")
    curated_starter_code = question.get("starter_code") or get_default_starter_code()
    variation_key = uuid4().hex[:12]

    if not GEMINI_API_KEY or not client:
        return get_fallback_problem_json(question)

    if enforce_signature:
        signature_rule = f"""6. Starter code must use this exact signature and class name:
{curated_starter_code}"""
    else:
        signature_rule = (
            "6. Choose one clear, descriptive Python method signature inside "
            "class Solution that matches this specific problem (for example "
            "def longestIncreasingSubsequence(self, nums)). Keep arguments "
            "JSON-friendly: int, float, str, list, nested list, or combinations "
            "of these. Do NOT name the method \"solve\" - name it after what it "
            "actually does."
        )

    avoid_repeats_rule = ""
    if recent_titles:
        titles_list = "\n".join(f"- {t}" for t in recent_titles[:15])
        avoid_repeats_rule = f"""
Avoid repeats:
Do not reuse the scenario, values, or title of any of these recently generated
problems for this topic. Generate something meaningfully different.
{titles_list}
"""

    prompt = f"""
You are ConceptVivaAI, a strict DSA practice problem generator.

Generate a coding practice problem in the exact style and tone of LeetCode.

Question metadata:
Question ID: {question_id}
Title: {title}
Topic: {topic}
Difficulty: {difficulty}
Pattern: {pattern}
Variation key (use this to vary scenario/values, do not include it in the output): {variation_key}
{avoid_repeats_rule}
Very important rules:
1. Do NOT provide the solution or optimized code.
2. Do NOT explain the answer.
3. The problem must read exactly like a real LeetCode problem page.
4. Give 2-3 examples. Each example must have input, output, and a short explanation.
5. Constraints must look like LeetCode constraints, for example "1 <= nums.length <= 10^4".
{signature_rule}
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
    "2 <= nums.length <= 10^4"
  ],
  "follow_up": "",
  "starter_code": "starter code"
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

        # Keep the bank id stable for later evaluation.
        result["question_id"] = question_id

        result.setdefault("title", title)
        result.setdefault("difficulty", difficulty)
        result.setdefault("topic", topic)
        result.setdefault("pattern", pattern)
        result.setdefault("description", f'Solve the problem "{title}".')
        result.setdefault("examples", [])
        result.setdefault("constraints", [])
        result.setdefault("follow_up", "")

        if enforce_signature:
            result["starter_code"] = curated_starter_code
        else:
            starter = str(result.get("starter_code") or "").strip()
            if (
                not starter.startswith("class Solution:")
                or "def " not in starter
                or "def solve(" in starter
                or len(starter) > 1500
            ):
                starter = get_default_starter_code()
            result["starter_code"] = starter

        if not isinstance(result["examples"], list):
            result["examples"] = []

        if not isinstance(result["constraints"], list):
            result["constraints"] = []

        return result

    except Exception:
        return get_fallback_problem_json(question)


def build_problem_text_from_json(problem_json):
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


def _score_from_runner(runner_result):
    if not runner_result or not runner_result.get("supported"):
        return None
    total = int(runner_result.get("total", 0) or 0)
    passed = int(runner_result.get("passed", 0) or 0)
    if total <= 0:
        return 0.0
    return round((passed / total) * 10, 1)


def evaluate_bank_dsa_solution_with_gemini(question, problem_text, solution):
    """Evaluate a curated question with the runner when available."""
    title = question.get("title", "DSA Problem")
    topic = question.get("topic", "DSA")
    difficulty = question.get("difficulty", "Medium")
    pattern = question.get("pattern", "General DSA")

    runner_result = run_question_tests(
        question=question,
        solution=solution,
        enabled=ENABLE_CODE_EXECUTION,
    )
    runner_score = _score_from_runner(runner_result)

    base_result = {
        "score": runner_score if runner_score is not None else 0,
        "feedback": "Hidden tests were executed." if runner_result.get("supported") else "Code execution is disabled; using server-side AI review.",
        "optimized_approach": "AI explanation is unavailable right now.",
        "optimized_code": "AI optimized code is unavailable right now.",
        "explanation": "Enable Gemini for detailed teaching feedback.",
        "time_complexity": "N/A",
        "space_complexity": "N/A",
        "test_cases": runner_result.get("test_cases", []),
        "runner_supported": bool(runner_result.get("supported")),
        "passed": int(runner_result.get("passed", 0) or 0),
        "total": int(runner_result.get("total", 0) or 0),
    }

    if not GEMINI_API_KEY or not client:
        if runner_result.get("supported"):
            if runner_result.get("all_passed"):
                base_result["feedback"] = "Your code passed all hidden tests for this curated question."
            else:
                base_result["feedback"] = "Your code failed one or more hidden tests. Review the failing cases and edge conditions."
        else:
            base_result["score"] = 0
            base_result["feedback"] = "Gemini and secure code execution are unavailable, so this attempt cannot be reliably scored."
        return base_result

    prompt = f"""
You are ConceptVivaAI, a strict DSA code reviewer.

Question metadata:
Title: {title}
Topic: {topic}
Difficulty: {difficulty}
Pattern: {pattern}

Problem:
{problem_text}

User Solution:
{solution}

Review the solution for logic, edge cases, time complexity, and space complexity.
Provide a correct optimized approach and complete optimized Python code using the
same function signature shown in the problem. Do not invent a different problem.

Return only valid JSON:
{{
  "score": number from 0 to 10,
  "feedback": "clear review",
  "optimized_approach": "best approach",
  "optimized_code": "complete Python code",
  "explanation": "teacher-style explanation",
  "time_complexity": "Big-O",
  "space_complexity": "Big-O"
}}
"""

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        ai_result = extract_json(response.text) or {}
    except Exception:
        ai_result = {}

    if runner_score is not None:
        # Hidden tests are the correctness authority.
        ai_result["score"] = runner_score
    else:
        try:
            ai_result["score"] = max(0.0, min(10.0, float(ai_result.get("score", 5))))
        except Exception:
            ai_result["score"] = 5.0

    ai_result.setdefault("feedback", base_result["feedback"])
    ai_result.setdefault("optimized_approach", base_result["optimized_approach"])
    ai_result.setdefault("optimized_code", base_result["optimized_code"])
    ai_result.setdefault("explanation", base_result["explanation"])
    ai_result.setdefault("time_complexity", "N/A")
    ai_result.setdefault("space_complexity", "N/A")

    # Keep runner output separate from Gemini feedback.
    ai_result["test_cases"] = runner_result.get("test_cases", [])
    ai_result["runner_supported"] = bool(runner_result.get("supported"))
    ai_result["passed"] = int(runner_result.get("passed", 0) or 0)
    ai_result["total"] = int(runner_result.get("total", 0) or 0)
    return ai_result


def evaluate_custom_dsa_solution_with_gemini(request):
    if not GEMINI_API_KEY or not client:
        return {
            "score": 0,
            "feedback": "This custom problem has no curated hidden tests and Gemini is unavailable, so it cannot be reliably scored.",
            "optimized_approach": "AI review unavailable.",
            "optimized_code": "AI review unavailable.",
            "explanation": "Use a curated bank question for deterministic hidden-test scoring.",
            "time_complexity": "N/A",
            "space_complexity": "N/A",
            "test_cases": [],
            "runner_supported": False,
            "passed": 0,
            "total": 0,
        }

    prompt = f"""
You are ConceptVivaAI, a strict DSA solution evaluator.

DSA Topic: {request.topic}
Difficulty: {request.difficulty}

Problem:
{request.problem}

User Solution:
{request.solution}

Evaluate semantic correctness, edge cases, time/space complexity and code quality.
Return only valid JSON:
{{
  "score": number from 0 to 10,
  "feedback": "clear review",
  "optimized_approach": "best approach",
  "optimized_code": "complete Python code",
  "explanation": "teacher-style explanation",
  "time_complexity": "Big-O",
  "space_complexity": "Big-O"
}}
"""
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        result = extract_json(response.text) or {}
    except Exception:
        result = {}

    try:
        result["score"] = max(0.0, min(10.0, float(result.get("score", 5))))
    except Exception:
        result["score"] = 5.0

    result.setdefault("feedback", "Server-side AI review completed.")
    result.setdefault("optimized_approach", "Review the algorithmic pattern and edge cases.")
    result.setdefault("optimized_code", "Optimized code unavailable.")
    result.setdefault("explanation", "Explanation unavailable.")
    result.setdefault("time_complexity", "N/A")
    result.setdefault("space_complexity", "N/A")
    result["test_cases"] = []
    result["runner_supported"] = False
    result["passed"] = 0
    result["total"] = 0
    return result


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
    """Legacy helper kept for compatibility with older tests/components.

    New curated execution is question-specific and lives in dsa_runner.py.
    """
    representative_titles = {
        "arrays": "Two Sum",
        "strings": "Valid Palindrome",
        "stack": "Valid Parentheses",
        "binary search": "Search Insert Position",
        "dynamic programming": "Climbing Stairs",
    }
    title = representative_titles.get(get_topic_key(topic))
    question = get_dsa_question_by_title(title) if title else None
    if not question:
        return []
    return question.get("runner", {}).get("tests", [])


def run_python_tests(topic, solution):
    """Backward-compatible topic runner.

    The real app extracts Question ID and runs that exact question. This helper
    selects one representative curated problem only for old tests/callers.
    """
    representative_titles = {
        "arrays": "Two Sum",
        "strings": "Valid Palindrome",
        "stack": "Valid Parentheses",
        "binary search": "Search Insert Position",
        "dynamic programming": "Climbing Stairs",
    }
    title = representative_titles.get(get_topic_key(topic))
    question = get_dsa_question_by_title(title) if title else None
    return run_question_tests(question, solution, ENABLE_CODE_EXECUTION)


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
