"""Validation of AI-generated DSA signatures and sample tests.

Gemini output is treated as untrusted input. A test case survives only if:
- its input decodes to exactly the declared parameters (JSON object keyed by name,
  or a JSON array in parameter order),
- every argument and the expected output match their declared types exactly
  (bool is not accepted as int, floats must be finite),
- it stays within size limits,
- it does not duplicate another case, and no other case gives a different expected
  output for the same input (such conflicts drop every case involved).
The starter code is rebuilt on the server from the validated signature, so the
code the student edits always matches what the harness calls.
"""
from __future__ import annotations

import json
import keyword
import math
import re

MIN_EXECUTABLE_TESTS = 2
MAX_TESTS = 8
MAX_LIST_LEN = 1000
MAX_NESTED_LEN = 200
MAX_STR_LEN = 1000
MAX_ABS_INT = 10**12
MAX_CASE_CHARS = 4000

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,39}$")
_FORBIDDEN_NAMES = {"self", "cls", "Solution", "__init__"}


class InvalidSignature(ValueError):
    pass


def _valid_identifier(name: str) -> bool:
    return bool(_IDENTIFIER.match(name or "")) and not keyword.iskeyword(name) and \
        name not in _FORBIDDEN_NAMES and not name.startswith("__")


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and abs(value) <= MAX_ABS_INT


def _is_float(value) -> bool:
    # JSON has no int/float distinction for whole numbers, so ints are accepted here.
    return (isinstance(value, float) and math.isfinite(value)) or _is_int(value)


def _is_str(value) -> bool:
    return isinstance(value, str) and len(value) <= MAX_STR_LEN


_SCALARS = {"int": _is_int, "float": _is_float, "str": _is_str, "bool": lambda v: isinstance(v, bool)}


def check_value(value, type_name: str) -> bool:
    if type_name in _SCALARS:
        return _SCALARS[type_name](value)
    if type_name.startswith("list[list[") and type_name.endswith("]]"):
        inner = type_name[len("list[list["):-2]
        return (
            isinstance(value, list) and len(value) <= MAX_NESTED_LEN
            and all(isinstance(row, list) and len(row) <= MAX_NESTED_LEN
                    and all(_SCALARS[inner](item) for item in row) for row in value)
        )
    if type_name.startswith("list[") and type_name.endswith("]"):
        inner = type_name[len("list["):-1]
        return isinstance(value, list) and len(value) <= MAX_LIST_LEN and all(_SCALARS[inner](item) for item in value)
    return False


def compare_mode(return_type: str, order_matters: bool) -> str:
    if return_type == "float":
        return "approx"
    if return_type == "list[float]":
        return "approx_list"
    if return_type.startswith("list[") and not order_matters:
        return "unordered_outer"
    return "exact"


def build_starter_code(function_name: str, parameters: list[dict]) -> str:
    hints = {
        "int": "int", "float": "float", "str": "str", "bool": "bool",
        "list[int]": "List[int]", "list[float]": "List[float]", "list[str]": "List[str]",
        "list[bool]": "List[bool]", "list[list[int]]": "List[List[int]]", "list[list[str]]": "List[List[str]]",
    }
    args = ", ".join(f"{p['name']}: {hints[p['type']]}" for p in parameters)
    return (
        "class Solution:\n"
        f"    def {function_name}(self, {args}):\n"
        "        # Write your code here\n"
        "        pass"
    )


def validate_signature(function_name: str, parameters: list[dict], return_type: str) -> None:
    if not _valid_identifier(function_name):
        raise InvalidSignature("function name is not a valid Python identifier")
    names = [p["name"] for p in parameters]
    if not names or len(names) > 6:
        raise InvalidSignature("between 1 and 6 parameters are required")
    if len(set(names)) != len(names):
        raise InvalidSignature("parameter names must be unique")
    if not all(_valid_identifier(name) for name in names):
        raise InvalidSignature("parameter names must be valid Python identifiers")
    if return_type not in _SCALARS and not return_type.startswith("list["):
        raise InvalidSignature("unsupported return type")


def _decode_args(raw: str, parameters: list[dict]):
    value = json.loads(raw)
    names = [p["name"] for p in parameters]
    if isinstance(value, dict):
        if set(value) != set(names):
            raise ValueError("input keys do not match the parameters")
        return [value[name] for name in names]
    if isinstance(value, list) and len(value) == len(names):
        return value
    raise ValueError("input must be an object keyed by parameter name")


def validate_tests(raw_cases: list[dict], parameters: list[dict], return_type: str) -> tuple[list[dict], list[dict]]:
    """Return (accepted, rejected). Each accepted case is {"args": [...], "expected": ...}."""
    accepted, rejected = [], []
    seen: dict[str, object] = {}
    conflicting: set[str] = set()

    for index, case in enumerate(raw_cases[: MAX_TESTS * 2]):
        raw_input = case.get("input_json", "")
        raw_expected = case.get("expected_output_json", "")
        if len(raw_input) + len(raw_expected) > MAX_CASE_CHARS:
            rejected.append({"index": index, "reason": "too large"})
            continue
        try:
            args = _decode_args(raw_input, parameters)
            expected = json.loads(raw_expected)
        except (ValueError, TypeError):
            rejected.append({"index": index, "reason": "malformed JSON or wrong parameters"})
            continue
        bad_arg = next((p["name"] for p, a in zip(parameters, args) if not check_value(a, p["type"])), None)
        if bad_arg:
            rejected.append({"index": index, "reason": f"argument '{bad_arg}' does not match its type"})
            continue
        if not check_value(expected, return_type):
            rejected.append({"index": index, "reason": "expected output does not match the return type"})
            continue

        key = json.dumps(args, sort_keys=True)
        if key in seen:
            if json.dumps(seen[key], sort_keys=True) != json.dumps(expected, sort_keys=True):
                conflicting.add(key)
            rejected.append({"index": index, "reason": "duplicate input"})
            continue
        seen[key] = expected
        accepted.append({"args": args, "expected": expected, "_key": key})

    if conflicting:
        for case in accepted:
            if case["_key"] in conflicting:
                rejected.append({"index": None, "reason": "same input has different expected outputs"})
        accepted = [case for case in accepted if case["_key"] not in conflicting]

    for case in accepted:
        case.pop("_key", None)
    return accepted[:MAX_TESTS], rejected


def format_args(parameters: list[dict], args: list) -> str:
    return ", ".join(f"{p['name']} = {json.dumps(a)}" for p, a in zip(parameters, args))
