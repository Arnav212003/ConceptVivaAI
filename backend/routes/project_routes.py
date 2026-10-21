from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from crud import (
    create_project_challenge,
    decode_project_challenge,
    get_project_challenge_by_id,
)
from database import get_db
from rate_limit import enforce_rate_limit
from schemas import (
    ProjectChallengeRequest,
    ProjectSubmissionRequest,
    SaveProjectAttemptRequest,
)
from security import create_evaluation_receipt, get_current_session_id
from serializers import serialize_project_attempt
from services.grading.evaluators import STATUS_COMPLETED
from services.project_service import (
    AUTO_PROJECT_TOPICS,
    build_full_source_bundle,
    build_project_submission_manifest,
    evaluate_project_submission_with_gemini,
    generate_project_challenge_with_gemini,
    normalize_project_review,
    save_verified_project_attempt,
)

router = APIRouter(tags=["project"])

MAX_PROJECT_SOURCE_CHARS = 2_200_000


@router.post("/generate-project-challenge")
async def generate_project_challenge(
    request: ProjectChallengeRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    topic = request.topic
    if request.auto_topic or not topic.strip():
        topic = "AI selected: " + AUTO_PROJECT_TOPICS.get(request.domain, "a useful practical project")

    challenge = await generate_project_challenge_with_gemini(
        domain=request.domain,
        topic=topic,
        difficulty=request.difficulty,
    )

    stored_challenge = await run_in_threadpool(
        create_project_challenge,
        db,
        {
            "session_id": session_id,
            "domain": request.domain,
            "topic": topic[:255],
            "difficulty": request.difficulty,
            "project_title": challenge.get("project_title", "Project Challenge"),
            "challenge": challenge,
        },
    )

    return {
        "mode": "project_challenge",
        "challenge_id": stored_challenge.challenge_id,
        "challenge": challenge,
        "message": "Project challenge generated and stored successfully.",
    }


@router.post("/evaluate-project-submission")
async def evaluate_project_submission(
    request: ProjectSubmissionRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    stored_challenge = await run_in_threadpool(
        get_project_challenge_by_id, db, session_id, request.challenge_id
    )

    if not stored_challenge:
        raise HTTPException(status_code=404, detail="Active project challenge not found for this session.")

    challenge = decode_project_challenge(stored_challenge.challenge_json)
    project_files = [item.model_dump() for item in request.files]

    if not project_files and not request.submission.strip():
        raise HTTPException(status_code=400, detail="Submit the complete project source folder before evaluation.")

    total_source_chars = sum(len(item.get("content", "")) for item in project_files)
    if total_source_chars > MAX_PROJECT_SOURCE_CHARS:
        raise HTTPException(
            status_code=413,
            detail="Readable project source is too large. Keep source files under 2.2 million characters after excluding dependencies/build output.",
        )

    review = normalize_project_review(
        await evaluate_project_submission_with_gemini(
            domain=stored_challenge.domain,
            topic=stored_challenge.topic,
            difficulty=stored_challenge.difficulty,
            challenge=challenge,
            submission=request.submission,
            project_files=project_files,
            project_notes=request.project_notes,
        )
    )

    # Store source when possible; fallback to a file manifest.
    if project_files:
        stored_submission = build_full_source_bundle(project_files) or build_project_submission_manifest(
            project_files, request.project_notes
        )
    else:
        stored_submission = request.submission

    attempt = await run_in_threadpool(
        save_verified_project_attempt, db, session_id, stored_challenge, challenge, stored_submission, review
    )
    review["challenge_id"] = stored_challenge.challenge_id
    review["verified_challenge"] = True
    review["saved_attempt"] = serialize_project_attempt(attempt)
    review["evaluation_receipt"] = (
        create_evaluation_receipt(
            session_id=session_id,
            kind="project_attempt",
            score=review["score"],
            verdict=review["verdict"],
            metadata={"challenge_id": stored_challenge.challenge_id},
        )
        if review["evaluation_status"] == STATUS_COMPLETED
        else ""
    )
    return review


@router.post("/save-project-attempt")
async def save_project_attempt(
    request: SaveProjectAttemptRequest,
    http_request: Request,
    session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db),
):
    """Legacy compatibility endpoint. Client project scores are ignored."""
    enforce_rate_limit(http_request, bucket="ai", session_id=session_id)
    if not request.challenge_id:
        raise HTTPException(status_code=400, detail="challenge_id is required for verified project saving.")

    stored_challenge = await run_in_threadpool(
        get_project_challenge_by_id, db, session_id, request.challenge_id
    )
    if not stored_challenge:
        raise HTTPException(status_code=404, detail="Active project challenge not found for this session.")

    challenge = decode_project_challenge(stored_challenge.challenge_json)
    review = normalize_project_review(
        await evaluate_project_submission_with_gemini(
            domain=stored_challenge.domain,
            topic=stored_challenge.topic,
            difficulty=stored_challenge.difficulty,
            challenge=challenge,
            submission=request.submission,
        )
    )
    attempt = await run_in_threadpool(
        save_verified_project_attempt, db, session_id, stored_challenge, challenge, request.submission, review
    )
    return {
        "message": "Project attempt re-evaluated and saved by backend.",
        "verified_challenge": True,
        "evaluation_status": review["evaluation_status"],
        "attempt": serialize_project_attempt(attempt),
    }
