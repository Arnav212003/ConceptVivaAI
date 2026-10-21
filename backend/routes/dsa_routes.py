from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from crud import create_dsa_attempt
from database import get_db
from judge import client as judge_client
from rate_limit import enforce_rate_limit
from schemas import (
    AIPracticeQuestionRequest,
    DSAEvaluateRequest,
    DSAMockSetRequest,
    DSAOwnQuestionRequest,
    DSAPracticeQuestionRequest,
    DSAProblemRequest,
    SaveDSAAttemptRequest,
)
from security import create_evaluation_receipt, get_current_session_id
from serializers import serialize_dsa_attempt
from services.dsa_bank import (
    DSA_QUESTION_BANK,
    get_all_dsa_questions,
    get_dsa_mock_set,
    get_dsa_practice_question,
    get_dsa_question_by_id,
    get_dsa_questions_by_difficulty,
)
from services.dsa_service import (
    TIER_VERIFIED,
    build_problem_text_from_json,
    evaluate_bank_dsa_solution,
    evaluate_custom_dsa_solution,
    generate_ai_practice_question,
    generate_dsa_problem_json_from_gemini,
    get_default_starter_code,
    get_fallback_dsa_problem,
    get_question_tier,
    is_hidden_test_available,
    judge_available,
)
from services.grading.evaluators import STATUS_COMPLETED
from utils import (
    extract_question_id_from_problem_text,
    get_difficulty_distribution,
    public_dsa_question,
)

router = APIRouter(tags=["dsa"])


@router.get("/dsa-question-bank")
def dsa_question_bank():
    return {
        "total": len(DSA_QUESTION_BANK),
        "questions": get_all_dsa_questions(),
    }


@router.get("/dsa-question-bank/stats")
def dsa_question_bank_stats():
    enabled = judge_available()
    return {
        "total": len(DSA_QUESTION_BANK),
        "easy": len(get_dsa_questions_by_difficulty("Easy")),
        "medium": len(get_dsa_questions_by_difficulty("Medium")),
        "hard": len(get_dsa_questions_by_difficulty("Hard")),
        "tier": TIER_VERIFIED,
        # Bank questions are hidden-test scored only when the isolated judge is up.
        "hidden_tests_enabled": enabled,
        "judge": {"enabled": enabled},
        "ai_practice": {
            "tier": "ai_generated",
            "total": "unlimited",
            "note": "Any topic, generated on demand via Gemini. Scored by AI review, not hidden tests.",
        },
    }


def _practice_response(mode, question, problem_json, message):
    return {
        "mode": mode,
        "question": public_dsa_question(question),
        "problem": build_problem_text_from_json(problem_json),
        "problem_json": problem_json,
        "starter_code": problem_json.get("starter_code", get_default_starter_code()),
        "tier": get_question_tier(runner_supported=is_hidden_test_available(question)),
        "message": message,
    }


def _fallback_practice_response(mode, request, message):
    return {
        "mode": mode,
        "question": None,
        "problem": get_fallback_dsa_problem(request.topic, request.difficulty),
        "problem_json": None,
        "starter_code": get_default_starter_code(),
        "tier": get_question_tier(runner_supported=False),
        "message": message,
    }


@router.post("/generate-dsa-mock-set")
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


@router.post("/generate-dsa-practice-question")
async def generate_dsa_practice_question(
    request: DSAPracticeQuestionRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
):
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    question = get_dsa_practice_question(topic=request.topic, difficulty=request.difficulty)
    if not question:
        return _fallback_practice_response(
            "practice", request, "No matching question found in DSA bank. Fallback problem returned."
        )
    problem_json = await generate_dsa_problem_json_from_gemini(question)
    return _practice_response("practice", question, problem_json, "Practice question generated successfully.")


@router.post("/generate-own-dsa-question")
async def generate_own_dsa_question(
    request: DSAOwnQuestionRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
):
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    question = get_dsa_question_by_id(request.question_id) if request.question_id else None
    is_bank_question = bool(question)

    if not question:
        question = {
            "id": "custom_user_question",
            "title": request.title,
            "topic": request.topic,
            "difficulty": request.difficulty,
            "pattern": request.pattern,
            "source": "User Provided",
        }

    problem_json = await generate_dsa_problem_json_from_gemini(
        question,
        enforce_signature=is_bank_question,
    )
    response = _practice_response(
        "own_question", question, problem_json, "Own question converted into practice problem successfully."
    )
    if not is_bank_question:
        response["tier"] = get_question_tier(runner_supported=False)
    return response


@router.post("/generate-dsa-problem")
async def generate_dsa_problem(
    request: DSAProblemRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
):
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    question = get_dsa_practice_question(topic=request.topic, difficulty=request.difficulty)
    if not question:
        return _fallback_practice_response(
            "practice", request, "No matching question found in new DSA bank. Fallback problem returned."
        )
    problem_json = await generate_dsa_problem_json_from_gemini(question)
    return _practice_response("practice", question, problem_json, "DSA problem generated from curated question bank.")


@router.post("/generate-ai-practice-question")
async def generate_ai_practice_question_route(
    request: AIPracticeQuestionRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
):
    """Generate a free-topic DSA problem for AI-reviewed practice."""
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    recent_titles = [t.strip()[:150] for t in request.recent_titles if t and t.strip()][:15]
    question, problem_json = await generate_ai_practice_question(
        request.topic,
        request.difficulty,
        recent_titles=recent_titles,
    )
    response = _practice_response(
        "ai_practice", question, problem_json, "AI practice question generated. Scored by AI review, not hidden tests."
    )
    response["tier"] = get_question_tier(runner_supported=False)
    return response


def _status_label(result):
    if result.get("evaluation_status") != STATUS_COMPLETED or result.get("score") is None:
        return "Unavailable"
    return "Passed" if result["score"] >= 8 else "Needs Improvement"


async def _evaluate(problem_text, solution, topic, difficulty, request_like, session_id):
    """Shared evaluation used by the evaluate and legacy save endpoints."""
    question_id = extract_question_id_from_problem_text(problem_text)
    question = get_dsa_question_by_id(question_id) if question_id else None

    if question:
        judge_result = None
        if is_hidden_test_available(question):
            judge_result = await judge_client.judge_and_wait(question, solution, session_id=session_id)
        result = await evaluate_bank_dsa_solution(question, problem_text, solution, judge_result)
        problem_name = question.get("title", "DSA Problem")
        stored_topic = question.get("topic", topic)
        stored_difficulty = question.get("difficulty", difficulty)
    else:
        result = await evaluate_custom_dsa_solution(request_like)
        problem_name = "Custom DSA Problem"
        stored_topic = topic
        stored_difficulty = difficulty

    if result.get("score") is not None:
        result["score"] = max(0.0, min(10.0, float(result["score"])))
    result["status"] = _status_label(result)
    # Verified tier only when hidden tests really produced the score.
    result["tier"] = get_question_tier(runner_supported=result.get("scoring_method") == "hidden_tests")
    return question_id, result, problem_name, stored_topic, stored_difficulty


def _attempt_record(session_id, mode, topic, difficulty, problem_name, problem, solution, result):
    judge = result.get("judge") or {}
    return {
        "session_id": session_id,
        "mode": mode,
        "topic": topic,
        "difficulty": difficulty,
        "problem_name": problem_name,
        "problem": problem,
        "solution": solution,
        "score": result.get("score"),
        "status": result["status"],
        "feedback": result.get("feedback", ""),
        "tier": result["tier"],
        "evaluation_status": result.get("evaluation_status", "unavailable"),
        "prompt_version": result.get("prompt_version", ""),
        "model_name": result.get("model", ""),
        "integrity_flags": result.get("integrity_flags", []),
        "scoring_method": result.get("scoring_method", "ai_rubric"),
        "judge_verdict": judge.get("verdict", ""),
        "judge_submission_id": judge.get("submission_id", ""),
        "tests_passed": result.get("passed", 0),
        "tests_total": result.get("total", 0),
    }


@router.post("/evaluate-dsa-solution")
async def evaluate_dsa_solution(
    request: DSAEvaluateRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    question_id, result, problem_name, stored_topic, stored_difficulty = await _evaluate(
        request.problem, request.solution, request.topic, request.difficulty, request, session_id
    )

    if result["evaluation_status"] == STATUS_COMPLETED:
        result["evaluation_receipt"] = create_evaluation_receipt(
            session_id=session_id,
            kind="dsa_attempt",
            score=result["score"],
            verdict=result["status"],
            metadata={"question_id": question_id or "custom", "mode": request.mode[:30],
                      "tier": result["tier"]},
        )
    else:
        result["evaluation_receipt"] = ""

    if request.save_attempt:
        attempt = await run_in_threadpool(
            create_dsa_attempt,
            db,
            _attempt_record(session_id, request.mode, stored_topic, stored_difficulty,
                            problem_name, request.problem, request.solution, result),
        )
        result["saved_attempt"] = serialize_dsa_attempt(attempt)

    return result


@router.post("/save-dsa-attempt")
async def save_dsa_attempt(
    request: SaveDSAAttemptRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db),
):
    """Legacy save endpoint. The backend still re-evaluates the attempt."""
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    eval_request = DSAEvaluateRequest(
        topic=request.topic,
        difficulty=request.difficulty,
        problem=request.problem or request.problem_name,
        solution=request.solution or "class Solution:\n    def solve(self):\n        pass",
        mode=request.mode,
        save_attempt=False,
    )
    _, result, problem_name, topic, difficulty = await _evaluate(
        eval_request.problem, eval_request.solution, request.topic, request.difficulty, eval_request, session_id
    )
    if problem_name == "Custom DSA Problem":
        problem_name = request.problem_name
    attempt = await run_in_threadpool(
        create_dsa_attempt,
        db,
        _attempt_record(session_id, request.mode, topic, difficulty, problem_name,
                        eval_request.problem, eval_request.solution, result),
    )
    return {
        "message": "DSA attempt re-evaluated and saved by backend.",
        "evaluation_status": result["evaluation_status"],
        "attempt": serialize_dsa_attempt(attempt),
    }
