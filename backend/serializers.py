"""Converts SQLAlchemy ORM rows into JSON-safe response dicts."""
import json

from crud import decode_project_challenge
from utils import format_datetime


def _decode_json_field(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _evaluation_fields(item):
    return {
        "evaluation_status": getattr(item, "evaluation_status", None) or "completed",
        "prompt_version": getattr(item, "prompt_version", None) or "",
        "model_name": getattr(item, "model_name", None) or "",
        "integrity_flags": _decode_json_field(getattr(item, "integrity_flags", None), []),
    }


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
        **_evaluation_fields(item),
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


def _dsa_test_source(item) -> str:
    """Where tests_passed/tests_total came from. Derived, so old rows need no migration."""
    if not (item.tests_total or 0):
        return "none"
    return "hidden_tests" if item.scoring_method == "hidden_tests" else "ai_generated_samples"


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
        "tier": item.tier,
        **_evaluation_fields(item),
        "scoring_method": item.scoring_method or "ai_rubric",
        "judge_verdict": item.judge_verdict or "",
        "tests_passed": item.tests_passed or 0,
        "tests_total": item.tests_total or 0,
        "test_source": _dsa_test_source(item),
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
        "architecture_review": item.architecture_review or "",
        "file_findings": _decode_json_field(item.file_findings, []),
        "bugs": _decode_json_field(item.bugs, []),
        "security_issues": _decode_json_field(item.security_issues, []),
        "missing_requirements": _decode_json_field(item.missing_requirements, []),
        "files_reviewed": item.files_reviewed or 0,
        **_evaluation_fields(item),
        "created_at": format_datetime(item.created_at),
    }
