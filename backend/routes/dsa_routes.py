from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from config import ENABLE_CODE_EXECUTION
from crud import create_dsa_attempt
from database import get_db
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
    evaluate_bank_dsa_solution_with_gemini,
    evaluate_custom_dsa_solution_with_gemini,
    generate_ai_practice_question,
    generate_dsa_problem_json_from_gemini,
    get_default_starter_code,
    get_fallback_dsa_problem,
    get_question_tier,
    is_hidden_test_available,
)
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
    return {
        "total": len(DSA_QUESTION_BANK),
        "easy": len(get_dsa_questions_by_difficulty("Easy")),
        "medium": len(get_dsa_questions_by_difficulty("Medium")),
        "hard": len(get_dsa_questions_by_difficulty("Hard")),
        "tier": TIER_VERIFIED,
        # Bank questions only get scored via hidden tests when this is true.
        # It defaults to false in .env.example (subprocess execution is not a
        # security boundary), so the frontend can show the real state instead
        # of unconditionally promising "Verified".
        "hidden_tests_enabled": ENABLE_CODE_EXECUTION,
        "ai_practice": {
            "tier": "ai_generated",
            "total": "unlimited",
            "note": "Any topic, generated on demand via Gemini. Scored by AI review, not hidden tests.",
        },
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
def generate_dsa_practice_question(
    request: DSAPracticeQuestionRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
):
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
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
            # No bank question matched, so evaluation can never resolve to a
            # real hidden-test runner either — this must not claim "verified".
            "tier": get_question_tier(runner_supported=False),
            "message": "No matching question found in DSA bank. Fallback problem returned.",
        }

    problem_json = generate_dsa_problem_json_from_gemini(question)
    problem_text = build_problem_text_from_json(problem_json)

    return {
        "mode": "practice",
        "question": public_dsa_question(question),
        "problem": problem_text,
        "problem_json": problem_json,
        "starter_code": problem_json.get("starter_code", get_default_starter_code()),
        "tier": get_question_tier(runner_supported=is_hidden_test_available(question)),
        "message": "Practice question generated successfully.",
    }


@router.post("/generate-own-dsa-question")
def generate_own_dsa_question(
    request: DSAOwnQuestionRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
):
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    question = get_dsa_question_by_id(request.question_id) if request.question_id else None
    is_bank_question = bool(question)
    tier = get_question_tier(runner_supported=is_bank_question and is_hidden_test_available(question))

    if not question:
        question = {
            "id": "custom_user_question",
            "title": request.title,
            "topic": request.topic,
            "difficulty": request.difficulty,
            "pattern": request.pattern,
            "source": "User Provided",
        }

    problem_json = generate_dsa_problem_json_from_gemini(
        question,
        enforce_signature=is_bank_question,
    )
    problem_text = build_problem_text_from_json(problem_json)

    return {
        "mode": "own_question",
        "question": public_dsa_question(question),
        "problem": problem_text,
        "problem_json": problem_json,
        "starter_code": problem_json.get("starter_code", get_default_starter_code()),
        "tier": tier,
        "message": "Own question converted into practice problem successfully.",
    }


@router.post("/generate-dsa-problem")
def generate_dsa_problem(
    request: DSAProblemRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
):
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
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
            "tier": get_question_tier(runner_supported=False),
            "message": "No matching question found in new DSA bank. Fallback problem returned.",
        }

    problem_json = generate_dsa_problem_json_from_gemini(question)
    problem_text = build_problem_text_from_json(problem_json)

    return {
        "problem": problem_text,
        "problem_json": problem_json,
        "starter_code": problem_json.get("starter_code", get_default_starter_code()),
        "question": public_dsa_question(question),
        "tier": get_question_tier(runner_supported=is_hidden_test_available(question)),
        "message": "DSA problem generated from curated question bank.",
    }


@router.post("/generate-ai-practice-question")
def generate_ai_practice_question_route(
    request: AIPracticeQuestionRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
):
    """AI Practice tier: unlimited topics, not limited to the 90 curated
    questions. Always AI-review scored (no hidden tests), so the response is
    always tagged tier="ai_generated" for the frontend badge.
    """
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    recent_titles = [t.strip()[:150] for t in request.recent_titles if t and t.strip()][:15]
    question, problem_json = generate_ai_practice_question(
        request.topic,
        request.difficulty,
        recent_titles=recent_titles,
    )
    problem_text = build_problem_text_from_json(problem_json)

    return {
        "mode": "ai_practice",
        "question": public_dsa_question(question),
        "problem": problem_text,
        "problem_json": problem_json,
        "starter_code": problem_json.get("starter_code", get_default_starter_code()),
        "tier": get_question_tier(runner_supported=False),
        "message": "AI practice question generated. Scored by AI review, not hidden tests.",
    }


@router.post("/evaluate-dsa-solution")
def evaluate_dsa_solution(
    request: DSAEvaluateRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    question_id = extract_question_id_from_problem_text(request.problem)
    question = get_dsa_question_by_id(question_id) if question_id else None

    if question:
        result = evaluate_bank_dsa_solution_with_gemini(
            question=question,
            problem_text=request.problem,
            solution=request.solution,
        )
        problem_name = question.get("title", "DSA Problem")
        stored_topic = question.get("topic", request.topic)
        stored_difficulty = question.get("difficulty", request.difficulty)
    else:
        result = evaluate_custom_dsa_solution_with_gemini(request)
        problem_name = "Custom DSA Problem"
        stored_topic = request.topic
        stored_difficulty = request.difficulty

    score = max(0.0, min(10.0, float(result.get("score", 0) or 0)))
    status = "Passed" if score >= 8 else "Needs Improvement"
    result["score"] = score
    result["status"] = status
    result_tier = get_question_tier(runner_supported=bool(result.get("runner_supported")))
    result["tier"] = result_tier
    result["evaluation_receipt"] = create_evaluation_receipt(
        session_id=session_id,
        kind="dsa_attempt",
        score=score,
        verdict=status,
        metadata={"question_id": question_id or "custom", "mode": request.mode[:30]},
    )

    if request.save_attempt:
        attempt = create_dsa_attempt(
            db,
            {
                "session_id": session_id,
                "mode": request.mode,
                "topic": stored_topic,
                "difficulty": stored_difficulty,
                "problem_name": problem_name,
                "problem": request.problem,
                "solution": request.solution,
                "score": score,
                "status": status,
                "feedback": result.get("feedback", ""),
                "tier": result_tier,
            },
        )
        result["saved_attempt"] = serialize_dsa_attempt(attempt)

    return result


@router.post("/save-dsa-attempt")
def save_dsa_attempt(
    request: SaveDSAAttemptRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db),
):
    """Legacy compatibility endpoint. Client score/status fields are ignored."""
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    eval_request = DSAEvaluateRequest(
        topic=request.topic,
        difficulty=request.difficulty,
        problem=request.problem or request.problem_name,
        solution=request.solution or "class Solution:\n    def solve(self):\n        pass",
        mode=request.mode,
        save_attempt=False,
    )
    question_id = extract_question_id_from_problem_text(eval_request.problem)
    question = get_dsa_question_by_id(question_id) if question_id else None
    if question:
        result = evaluate_bank_dsa_solution_with_gemini(question, eval_request.problem, eval_request.solution)
        problem_name = question.get("title", request.problem_name)
        topic = question.get("topic", request.topic)
        difficulty = question.get("difficulty", request.difficulty)
    else:
        result = evaluate_custom_dsa_solution_with_gemini(eval_request)
        problem_name = request.problem_name
        topic = request.topic
        difficulty = request.difficulty

    score = max(0.0, min(10.0, float(result.get("score", 0) or 0)))
    status = "Passed" if score >= 8 else "Needs Improvement"
    attempt = create_dsa_attempt(
        db,
        {
            "session_id": session_id,
            "mode": request.mode,
            "topic": topic,
            "difficulty": difficulty,
            "problem_name": problem_name,
            "problem": eval_request.problem,
            "solution": eval_request.solution,
            "score": score,
            "status": status,
            "feedback": result.get("feedback", ""),
            "tier": get_question_tier(runner_supported=bool(result.get("runner_supported"))),
        },
    )
    return {
        "message": "DSA attempt re-evaluated and saved by backend.",
        "attempt": serialize_dsa_attempt(attempt),
    }
