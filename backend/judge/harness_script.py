"""In-sandbox test harness. Executed as a standalone program by every executor.

Input  (stdin): {"runner": {...question runner metadata...}, "solution": "<python source>"}
Output (stdout): one line `__CV_RESULT__<json>` with per-test results.

This file must only use the standard library: it runs inside Judge0 or the sandbox
container, not inside the API. User prints are captured so they cannot corrupt the
result line. Process-level limits (CPU time, memory, processes, network) are
enforced by the executor, not here.
"""
import io
import json
import math
import sys
import time
from collections import Counter, defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple

RESULT_PREFIX = "__CV_RESULT__"
MAX_DISPLAY = 2000
MAX_CAPTURED_STDOUT = 64_000


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


class _CappedBuffer(io.StringIO):
    def write(self, text):
        if self.tell() < MAX_CAPTURED_STDOUT:
            return super().write(text[: MAX_CAPTURED_STDOUT - self.tell()])
        return len(text)


def build_list(values):
    dummy = ListNode()
    cur = dummy
    for value in values or []:
        cur.next = ListNode(value)
        cur = cur.next
    return dummy.next


def list_to_values(head, limit=10000):
    values, seen = [], set()
    while head is not None and len(values) < limit:
        if id(head) in seen:
            values.append("<cycle>")
            break
        seen.add(id(head))
        values.append(head.val)
        head = head.next
    return values


def build_tree(values):
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue, index = deque([root]), 1
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
    out, queue = [], deque([root])
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
    try:
        if mode == "any_of":
            return actual in test.get("expected_any", [expected])
        if mode == "approx":
            return math.isclose(float(actual), float(expected), rel_tol=1e-7, abs_tol=1e-7)
        if mode == "approx_list":
            return len(actual) == len(expected) and all(
                math.isclose(float(a), float(b), rel_tol=1e-7, abs_tol=1e-7)
                for a, b in zip(actual, expected)
            )
        if mode == "unordered_outer":
            return sorted(canonical(i) for i in actual) == sorted(canonical(i) for i in expected)
        if mode == "unordered_nested":
            return sorted(canonical(sorted(i)) for i in actual) == sorted(canonical(sorted(i)) for i in expected)
    except Exception:
        return False
    return actual == expected


def display(value):
    try:
        text = json.dumps(value, ensure_ascii=False)
    except Exception:
        text = repr(value)
    return text[:MAX_DISPLAY]


def emit(stdout, payload):
    stdout.write(RESULT_PREFIX + json.dumps(payload, ensure_ascii=False) + "\n")
    stdout.flush()


def main():
    real_stdout = sys.stdout
    payload = json.loads(sys.stdin.read())
    runner = payload["runner"]
    solution = payload["solution"]

    try:
        code = compile(solution, "<solution>", "exec")
    except (SyntaxError, ValueError) as exc:
        emit(real_stdout, {"phase": "compile", "error": f"{type(exc).__name__}: {exc}"[:MAX_DISPLAY]})
        return

    namespace = {
        "__builtins__": __builtins__, "__name__": "solution",
        "ListNode": ListNode, "TreeNode": TreeNode,
        "List": List, "Optional": Optional, "Dict": Dict, "Set": Set, "Tuple": Tuple,
        "Counter": Counter, "defaultdict": defaultdict, "deque": deque, "math": math,
    }
    captured = _CappedBuffer()
    sys.stdout = captured
    try:
        exec(code, namespace, namespace)
    except MemoryError:
        sys.stdout = real_stdout
        emit(real_stdout, {"phase": "load", "error": "MemoryError", "memory_exceeded": True})
        return
    except BaseException as exc:  # noqa: BLE001 - user code may raise anything
        sys.stdout = real_stdout
        emit(real_stdout, {"phase": "load", "error": f"{type(exc).__name__}: {exc}"[:MAX_DISPLAY]})
        return

    function_name = runner.get("function")
    solution_class = namespace.get("Solution")
    if solution_class is None or not callable(getattr(solution_class, function_name, None)):
        sys.stdout = real_stdout
        emit(real_stdout, {
            "phase": "compile",
            "error": f"Expected class Solution with method {function_name}(...)",
        })
        return

    arg_types = runner.get("arg_types") or []
    return_type = runner.get("return_type", "raw")
    compare_mode = runner.get("compare", "exact")
    mutate_index = runner.get("mutate_index")
    results = []

    for test in runner.get("tests", []):
        raw_args = test.get("args", [])
        args = [convert_arg(v, arg_types[i] if i < len(arg_types) else "raw") for i, v in enumerate(raw_args)]
        expected_display = display(test.get("expected_any") if "expected_any" in test else test.get("expected"))
        started = time.perf_counter()
        try:
            returned = getattr(solution_class(), function_name)(*args)
            if mutate_index is not None:
                mutation_type = arg_types[mutate_index] if mutate_index < len(arg_types) else "raw"
                kind = mutation_type if mutation_type in ("tree", "listnode") else "raw"
                actual = normalize_return(args[mutate_index], kind)
            else:
                actual = normalize_return(returned, return_type)
            status = "passed" if compare_values(actual, test, compare_mode) else "wrong_answer"
            actual_display = display(actual)
        except MemoryError:
            status, actual_display = "memory_exceeded", "MemoryError"
        except RecursionError:
            status, actual_display = "runtime_error", "RecursionError: maximum recursion depth exceeded"
        except BaseException as exc:  # noqa: BLE001
            status, actual_display = "runtime_error", f"{type(exc).__name__}: {exc}"[:MAX_DISPLAY]
        results.append({
            "input": display(raw_args),
            "expected_output": expected_display,
            "actual_output": actual_display,
            "status": status,
            "time_ms": round((time.perf_counter() - started) * 1000, 2),
        })

    sys.stdout = real_stdout
    emit(real_stdout, {"phase": "tests", "results": results, "stdout": captured.getvalue()[:2000]})


if __name__ == "__main__":
    main()
