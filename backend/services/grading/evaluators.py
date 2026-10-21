"""AI evaluators built on the LLM gateway.

Contract shared by every evaluator:
- `evaluation_status` is "completed" or "unavailable".
- When unavailable, `score` is None. No placeholder score is ever produced, so an
  outage can never be saved as a real grade or reach a dashboard average.
- When completed, the score is computed on the server from validated rubric points,
  then capped if a prompt-injection attempt was detected.
"""
from __future__ import annotations

import json

from services import llm
from services.grading import safety
from services.grading.prompts import (
    ANSWER_EVAL,
    ANSWER_RUBRIC,
    CODE_REVIEW,
    CODE_RUBRIC,
    PROJECT_REVIEW,
    PROJECT_RUBRIC,
    PromptSpec,
)
from services.grading.schemas import (
    AnswerEvaluationOutput,
    CodeReviewOutput,
    ProjectReviewOutput,
)

STATUS_COMPLETED = "completed"
STATUS_UNAVAILABLE = "unavailable"

ALLOWED_LEVELS = {"easy": "Easy", "medium": "Medium", "hard": "Hard",
                  "beginner": "Beginner", "intermediate": "Intermediate", "advanced": "Advanced"}

UNAVAILABLE_MESSAGE = (
    "AI evaluation is temporarily unavailable, so this attempt was not scored. "
    "Nothing was added to your averages. Please try again in a moment."
)


def normalize_level(level: str, default: str = "Medium") -> str:
    return ALLOWED_LEVELS.get((level or "").strip().lower(), default)


def verdict_for(score: float) -> str:
    if score >= 8:
        return "STRONG"
    if score >= 5:
        return "PARTIAL"
    return "WEAK"


def _meta(spec: PromptSpec) -> dict:
    return {"prompt_version": spec.id, "model": llm.current_model_name()}


def _finalize(spec, rubric, output, *, heuristic_signals, topic) -> dict:
    rubric_score = rubric.total(output.rubric)
    score, capped = safety.apply_integrity_cap(
        rubric_score,
        heuristic_signals=heuristic_signals,
        model_flagged=output.manipulation_attempt,
        topic=topic,
    )
    return {
        "evaluation_status": STATUS_COMPLETED,
        "score": score,
        "verdict": verdict_for(score),
        "rubric": rubric.breakdown(output.rubric),
        "rubric_score": rubric_score,
        "score_capped": capped,
        "integrity_flags": safety.integrity_flags(heuristic_signals, output.manipulation_attempt),
        **_meta(spec),
    }


def _unavailable(spec, reason: str, heuristic_signals: list[str], **fields) -> dict:
    return {
        "evaluation_status": STATUS_UNAVAILABLE,
        "unavailable_reason": reason,
        "score": None,
        "verdict": "UNAVAILABLE",
        "feedback": UNAVAILABLE_MESSAGE,
        "rubric": {},
        "rubric_score": None,
        "score_capped": False,
        "integrity_flags": safety.integrity_flags(heuristic_signals, False),
        **_meta(spec),
        **fields,
    }


# ------------------------------------------------------------------ answers


def build_answer_prompt(*, topic: str, level: str, question: str, answer: str, boundary: str) -> str:
    return "\n\n".join([
        f"Difficulty: {normalize_level(level)}",
        "Topic:\n" + safety.wrap_untrusted("topic", topic, boundary),
        "Interviewer question:\n" + safety.wrap_untrusted("question", question, boundary),
        "Student answer:\n" + safety.wrap_untrusted("student_answer", answer, boundary),
    ])


async def evaluate_answer(*, topic: str, level: str, question: str, answer: str,
                          spec: PromptSpec = ANSWER_EVAL) -> dict:
    signals = safety.detect_injection(answer)
    prompt = build_answer_prompt(
        topic=topic, level=level, question=question, answer=answer, boundary=safety.new_boundary()
    )
    try:
        output = await llm.generate_structured(
            "answer_eval",
            system_instruction=spec.system_instruction,
            prompt=prompt,
            schema=AnswerEvaluationOutput,
        )
    except llm.LLMUnavailableError as exc:
        return _unavailable(
            spec, exc.reason, signals,
            missing_points="", corrected_answer="", follow_up_question="",
            improvement="Submit again once AI evaluation is back.",
        )

    result = _finalize(spec, ANSWER_RUBRIC, output, heuristic_signals=signals, topic=topic)
    result.update(
        feedback=output.feedback,
        missing_points=output.missing_points,
        corrected_answer=output.corrected_answer,
        improvement=output.improvement,
        follow_up_question=output.follow_up_question,
    )
    if result["score_capped"]:
        result["feedback"] = (
            "Part of this answer tried to instruct the grader instead of answering the question, "
            f"so the score was capped at {safety.INJECTION_SCORE_CAP:g}/10. " + result["feedback"]
        )
    return result


# ------------------------------------------------------------------ DSA code


def build_code_prompt(*, metadata: dict, problem_text: str, solution: str, boundary: str) -> str:
    trusted = "\n".join(f"{key}: {value}" for key, value in metadata.items() if value)
    return "\n\n".join([
        "Problem metadata (trusted):\n" + trusted,
        "Problem statement:\n" + safety.wrap_untrusted("problem", problem_text, boundary),
        "Student solution (Python):\n" + safety.wrap_untrusted("solution", solution, boundary),
    ])


async def review_code(*, metadata: dict, problem_text: str, solution: str,
                      spec: PromptSpec = CODE_REVIEW) -> dict:
    signals = safety.detect_injection_in_code(solution)
    prompt = build_code_prompt(
        metadata=metadata, problem_text=problem_text, solution=solution, boundary=safety.new_boundary()
    )
    try:
        output = await llm.generate_structured(
            "code_review",
            system_instruction=spec.system_instruction,
            prompt=prompt,
            schema=CodeReviewOutput,
        )
    except llm.LLMUnavailableError as exc:
        return _unavailable(
            spec, exc.reason, signals,
            optimized_approach="AI review is unavailable right now.",
            optimized_code="",
            explanation="",
            time_complexity="N/A",
            space_complexity="N/A",
        )

    topic = str(metadata.get("Topic", ""))
    result = _finalize(spec, CODE_RUBRIC, output, heuristic_signals=signals, topic=topic)
    result.update(
        feedback=output.feedback,
        optimized_approach=output.optimized_approach,
        optimized_code=output.optimized_code,
        explanation=output.explanation,
        time_complexity=output.time_complexity or "N/A",
        space_complexity=output.space_complexity or "N/A",
    )
    return result


# ------------------------------------------------------------------ projects


def build_project_prompt(*, domain, topic, difficulty, challenge, source, file_count,
                         project_notes, boundary) -> str:
    return "\n\n".join([
        f"Difficulty: {normalize_level(difficulty, 'Beginner')}",
        f"Files submitted: {file_count if file_count else 'legacy text submission'}",
        "Domain:\n" + safety.wrap_untrusted("domain", domain, boundary),
        "Topic:\n" + safety.wrap_untrusted("topic", topic, boundary),
        "Assigned challenge:\n" + safety.wrap_untrusted(
            "challenge", json.dumps(challenge, indent=2, ensure_ascii=False), boundary
        ),
        "Student notes:\n" + safety.wrap_untrusted("notes", project_notes or "No notes.", boundary),
        "Complete project source:\n" + safety.wrap_untrusted("source", source, boundary),
    ])


async def review_project(*, domain, topic, difficulty, challenge, source, file_count,
                         project_notes="", spec: PromptSpec = PROJECT_REVIEW) -> dict:
    signals = sorted(set(
        safety.detect_injection_in_code(source) + safety.detect_injection(project_notes)
    ))
    empty_lists = {
        "file_findings": [], "bugs": [], "security_issues": [],
        "missing_requirements": [], "suggested_resources": [],
    }
    prompt = build_project_prompt(
        domain=domain, topic=topic, difficulty=difficulty, challenge=challenge, source=source,
        file_count=file_count, project_notes=project_notes, boundary=safety.new_boundary(),
    )
    try:
        output = await llm.generate_structured(
            "project_review",
            system_instruction=spec.system_instruction,
            prompt=prompt,
            schema=ProjectReviewOutput,
        )
    except llm.LLMUnavailableError as exc:
        return _unavailable(
            spec, exc.reason, signals,
            missing_points="", improved_approach="", next_steps="Submit again once AI review is back.",
            architecture_review="Not reviewed.", files_reviewed=file_count, **empty_lists,
        )

    result = _finalize(spec, PROJECT_RUBRIC, output, heuristic_signals=signals, topic=topic)
    result.update(
        feedback=output.feedback,
        architecture_review=output.architecture_review,
        file_findings=[item.model_dump() for item in output.file_findings],
        bugs=[item.model_dump() for item in output.bugs],
        security_issues=[item.model_dump() for item in output.security_issues],
        missing_requirements=list(output.missing_requirements),
        missing_points=output.missing_points,
        improved_approach=output.improved_approach,
        next_steps=output.next_steps,
        suggested_resources=list(output.suggested_resources),
        files_reviewed=file_count,
    )
    return result
