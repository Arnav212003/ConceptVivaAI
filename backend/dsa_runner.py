"""Small local DSA judge used for curated ConceptVivaAI questions.

This is intentionally disabled by default in production because Python subprocess
execution is not a security boundary. For local development it provides real
hidden-test execution. A production deployment should replace the subprocess
backend with a container/microVM judge while keeping this module's return shape.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _not_executed(message: str) -> dict[str, Any]:
    return {
        "supported": False,
        "all_passed": False,
        "passed": 0,
        "total": 0,
        "test_cases": [
            {
                "input": "Hidden tests",
                "expected_output": "Secure code runner enabled",
                "actual_output": message,
                "status": "Not Executed",
            }
        ],
    }


def run_question_tests(question: dict[str, Any] | None, solution: str, enabled: bool) -> dict[str, Any]:
    if not question or not question.get("runner"):
        return _not_executed("No runner metadata exists for this question.")

    if not enabled:
        return _not_executed(
            "Direct Python execution is disabled. Set ENABLE_CODE_EXECUTION=true only in a trusted local/sandbox environment."
        )

    if not solution or len(solution) > 30000:
        return _not_executed("Solution is empty or exceeds the 30,000 character limit.")

    payload = {
        "runner": question["runner"],
        "solution": solution,
    }

    runner_script = r'''
import ast
import json
import math
import os
import sys
from collections import Counter, defaultdict, deque
from typing import List, Optional, Dict, Set, Tuple

payload = json.loads(sys.stdin.read())
runner = payload["runner"]
solution = payload["solution"]

class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def build_list(values):
    if not values:
        return None
    dummy = ListNode()
    cur = dummy
    for value in values:
        cur.next = ListNode(value)
        cur = cur.next
    return dummy.next

def list_to_values(head, limit=10000):
    values = []
    seen = set()
    while head is not None and len(values) < limit:
        oid = id(head)
        if oid in seen:
            values.append("<cycle>")
            break
        seen.add(oid)
        values.append(head.val)
        head = head.next
    return values

def build_tree(values):
    if not values:
        return None
    if values[0] is None:
        return None
    root = TreeNode(values[0])
    queue = deque([root])
    index = 1
    while queue and index < len(values):
        node = queue.popleft()
        if index < len(values) and values[index] is not None:
            node.left = TreeNode(values[index])
            queue.append(node.left)
        index += 1
        if index < len(values) and values[index] is not None:
            node.right = TreeNode(values[index])
            queue.append(node.right)
        index += 1
    return root

def tree_to_values(root):
    if root is None:
        return []
    out = []
    queue = deque([root])
    while queue:
        node = queue.popleft()
        if node is None:
            out.append(None)
            continue
        out.append(node.val)
        queue.append(node.left)
        queue.append(node.right)
    while out and out[-1] is None:
        out.pop()
    return out

def convert_arg(value, arg_type):
    if arg_type == "listnode":
        return build_list(value)
    if arg_type == "listnode_list":
        return [build_list(item) for item in value]
    if arg_type == "tree":
        return build_tree(value)
    return value

def normalize_return(value, return_type):
    if return_type == "listnode":
        return list_to_values(value)
    if return_type == "tree":
        return tree_to_values(value)
    return value

def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return repr(value)

def compare_values(actual, test, mode):
    expected = test.get("expected")
    if mode == "any_of":
        choices = test.get("expected_any", [expected])
        return actual in choices
    if mode == "approx":
        try:
            return math.isclose(float(actual), float(expected), rel_tol=1e-7, abs_tol=1e-7)
        except Exception:
            return False
    if mode == "approx_list":
        try:
            return len(actual) == len(expected) and all(
                math.isclose(float(a), float(b), rel_tol=1e-7, abs_tol=1e-7)
                for a, b in zip(actual, expected)
            )
        except Exception:
            return False
    if mode == "unordered_outer":
        try:
            return sorted(canonical(item) for item in actual) == sorted(canonical(item) for item in expected)
        except Exception:
            return False
    if mode == "unordered_nested":
        try:
            norm_actual = sorted(canonical(sorted(item)) for item in actual)
            norm_expected = sorted(canonical(sorted(item)) for item in expected)
            return norm_actual == norm_expected
        except Exception:
            return False
    return actual == expected

def display(value):
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return repr(value)

# Compile first so syntax errors are reported cleanly.
try:
    compile(solution, "<user_solution>", "exec")
except Exception as exc:
    print(json.dumps({"fatal": f"SyntaxError: {exc}"}))
    raise SystemExit(0)

globals_dict = {
    "__builtins__": __builtins__,
    "ListNode": ListNode,
    "TreeNode": TreeNode,
    "List": List,
    "Optional": Optional,
    "Dict": Dict,
    "Set": Set,
    "Tuple": Tuple,
    "Counter": Counter,
    "defaultdict": defaultdict,
    "deque": deque,
    "math": math,
}

try:
    exec(solution, globals_dict, globals_dict)
except Exception as exc:
    print(json.dumps({"fatal": f"Import/definition error: {type(exc).__name__}: {exc}"}))
    raise SystemExit(0)

SolutionClass = globals_dict.get("Solution")
if SolutionClass is None:
    print(json.dumps({"fatal": "Expected a class named Solution."}))
    raise SystemExit(0)

function_name = runner.get("function")
arg_types = runner.get("arg_types") or []
return_type = runner.get("return_type", "raw")
compare_mode = runner.get("compare", "exact")
mutate_index = runner.get("mutate_index")
results = []
passed = 0

for test in runner.get("tests", []):
    raw_args = test.get("args", [])
    args = []
    for idx, value in enumerate(raw_args):
        arg_type = arg_types[idx] if idx < len(arg_types) else "raw"
        args.append(convert_arg(value, arg_type))

    try:
        instance = SolutionClass()
        function = getattr(instance, function_name)
        returned = function(*args)

        if mutate_index is not None:
            mutated = args[mutate_index]
            mutation_type = arg_types[mutate_index] if mutate_index < len(arg_types) else "raw"
            actual = normalize_return(mutated, "tree" if mutation_type == "tree" else ("listnode" if mutation_type == "listnode" else "raw"))
        else:
            actual = normalize_return(returned, return_type)

        ok = compare_values(actual, test, compare_mode)
        if ok:
            passed += 1

        expected_for_display = test.get("expected_any") if "expected_any" in test else test.get("expected")
        results.append({
            "input": display(raw_args),
            "expected_output": display(expected_for_display),
            "actual_output": display(actual),
            "status": "Passed" if ok else "Failed",
        })
    except Exception as exc:
        expected_for_display = test.get("expected_any") if "expected_any" in test else test.get("expected")
        results.append({
            "input": display(raw_args),
            "expected_output": display(expected_for_display),
            "actual_output": f"{type(exc).__name__}: {exc}",
            "status": "Failed",
        })

print(json.dumps({
    "passed": passed,
    "total": len(results),
    "all_passed": bool(results) and passed == len(results),
    "results": results,
}, ensure_ascii=False))
'''

    temp_dir = tempfile.mkdtemp(prefix="conceptviva_runner_")
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", runner_script],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=4,
            cwd=temp_dir,
            env={
                "PATH": os.environ.get("PATH", ""),
                "PYTHONIOENCODING": "utf-8",
            },
        )
    except subprocess.TimeoutExpired:
        return {
            "supported": True,
            "all_passed": False,
            "passed": 0,
            "total": len(question["runner"].get("tests", [])),
            "test_cases": [
                {
                    "input": "Hidden tests",
                    "expected_output": "Finish within 4 seconds",
                    "actual_output": "Time Limit Exceeded",
                    "status": "Failed",
                }
            ],
        }
    finally:
        try:
            Path(temp_dir).rmdir()
        except Exception:
            pass

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()

    if not stdout:
        return {
            "supported": True,
            "all_passed": False,
            "passed": 0,
            "total": len(question["runner"].get("tests", [])),
            "test_cases": [
                {
                    "input": "Code execution",
                    "expected_output": "Valid runner output",
                    "actual_output": stderr or "No output returned",
                    "status": "Failed",
                }
            ],
        }

    try:
        parsed = json.loads(stdout.splitlines()[-1])
    except Exception:
        return {
            "supported": True,
            "all_passed": False,
            "passed": 0,
            "total": len(question["runner"].get("tests", [])),
            "test_cases": [
                {
                    "input": "Code execution",
                    "expected_output": "Valid JSON runner output",
                    "actual_output": stdout[-1000:] or stderr,
                    "status": "Failed",
                }
            ],
        }

    if parsed.get("fatal"):
        return {
            "supported": True,
            "all_passed": False,
            "passed": 0,
            "total": len(question["runner"].get("tests", [])),
            "test_cases": [
                {
                    "input": "Code execution",
                    "expected_output": f"class Solution with {question['runner'].get('function')}(...)",
                    "actual_output": parsed["fatal"],
                    "status": "Failed",
                }
            ],
        }

    return {
        "supported": True,
        "all_passed": bool(parsed.get("all_passed")),
        "passed": int(parsed.get("passed", 0)),
        "total": int(parsed.get("total", 0)),
        "test_cases": parsed.get("results", []),
    }
