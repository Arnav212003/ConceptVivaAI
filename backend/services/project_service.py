"""Project challenge generation and review helpers."""
from crud import create_project_attempt, mark_project_challenge_completed
from services import llm
from services.grading import safety
from services.grading.evaluators import STATUS_COMPLETED, review_project, verdict_for
from services.grading.prompts import PROJECT_CHALLENGE
from services.grading.schemas import ProjectChallengeOutput

AUTO_PROJECT_TOPICS = {
    "Machine Learning": "a useful beginner ML project such as KNN, clustering, regression, classification or model evaluation",
    "Data Analytics": "a useful analytics project such as a sales dashboard, churn analysis or KPI analysis",
    "DSA": "a useful DSA project such as a path-finding visualizer, sorting visualizer or graph traversal tool",
    "System Design": "a useful system design project such as a URL shortener, rate limiter, notification system or chat system",
}


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
        "generated_by": "fallback",
    }


async def generate_project_challenge_with_gemini(domain, topic, difficulty):
    boundary = safety.new_boundary()
    prompt = "\n\n".join([
        f"Difficulty: {difficulty}",
        "Domain:\n" + safety.wrap_untrusted("domain", domain, boundary),
        "Topic:\n" + safety.wrap_untrusted("topic", topic, boundary),
    ])
    try:
        output = await llm.generate_structured(
            "project_challenge",
            system_instruction=PROJECT_CHALLENGE.system_instruction,
            prompt=prompt,
            schema=ProjectChallengeOutput,
            temperature=0.7,
        )
    except llm.LLMUnavailableError:
        return get_fallback_project_challenge(domain, topic, difficulty)

    return {
        **output.model_dump(),
        "dataset_columns": [column.model_dump() for column in output.dataset_columns],
        "domain": domain,
        "topic": topic,
        "difficulty": difficulty,
        "generated_by": "ai",
    }


def _project_file_bundle(project_files):
    """Create a file-by-file source bundle for review and history."""
    sections = []
    for item in project_files or []:
        path = str(item.get("path", "")).strip()
        content = str(item.get("content", ""))
        if not path:
            continue
        sections.append(f"\n===== FILE: {path} =====\n{content}\n===== END FILE: {path} =====")
    return "\n".join(sections)


def build_full_source_bundle(project_files):
    """Return submitted source code with file markers."""
    return _project_file_bundle(project_files)


def build_project_submission_manifest(project_files, project_notes=""):
    """Return a short file list when the full bundle is unavailable."""
    files = project_files or []
    lines = [f"Full project source submitted: {len(files)} files"]
    for item in files:
        path = str(item.get("path", "unknown"))
        content = str(item.get("content", ""))
        lines.append(f"- {path} ({len(content)} characters)")
    if project_notes.strip():
        lines.append("\nStudent notes:\n" + project_notes.strip())
    return "\n".join(lines)


async def evaluate_project_submission_with_gemini(
    domain,
    topic,
    difficulty,
    challenge,
    submission="",
    project_files=None,
    project_notes="",
):
    project_files = project_files or []
    full_source = _project_file_bundle(project_files)
    source_for_review = full_source if full_source else submission
    file_count = len(project_files)

    if not source_for_review.strip():
        # An empty submission is a real (deterministic) zero, not an AI outage.
        return {
            "evaluation_status": STATUS_COMPLETED,
            "score": 0.0,
            "verdict": "WEAK",
            "feedback": "No project source code was submitted.",
            "missing_points": "Submit the complete readable project source folder before evaluation.",
            "improved_approach": "Upload the complete source folder, excluding generated dependencies and binary files.",
            "next_steps": "Select the project folder and submit again.",
            "suggested_resources": [],
            "architecture_review": "Not evaluated.",
            "file_findings": [],
            "bugs": [],
            "security_issues": [],
            "missing_requirements": [],
            "files_reviewed": 0,
            "rubric": {},
            "integrity_flags": [],
            "prompt_version": "deterministic@empty_submission",
            "model": "none",
        }

    return await review_project(
        domain=domain,
        topic=topic,
        difficulty=difficulty,
        challenge=challenge,
        source=source_for_review,
        file_count=file_count,
        project_notes=project_notes,
    )


def normalize_project_review(review):
    """Fill display defaults. Unavailable reviews keep score None."""
    review = dict(review or {})
    if review.get("evaluation_status") == STATUS_COMPLETED and review.get("score") is not None:
        score = max(0.0, min(10.0, float(review["score"])))
        review["score"] = score
        review["verdict"] = verdict_for(score)
    else:
        review["evaluation_status"] = review.get("evaluation_status") or "unavailable"
        review["score"] = None
        review["verdict"] = "UNAVAILABLE"
    review.setdefault("feedback", "Project review completed.")
    review.setdefault("missing_points", "")
    review.setdefault("improved_approach", "")
    review.setdefault("next_steps", "")
    review.setdefault("suggested_resources", [])
    review.setdefault("architecture_review", "")
    review.setdefault("file_findings", [])
    review.setdefault("bugs", [])
    review.setdefault("security_issues", [])
    review.setdefault("missing_requirements", [])
    review.setdefault("files_reviewed", 0)
    review.setdefault("integrity_flags", [])
    return review


def save_verified_project_attempt(db, session_id, stored_challenge, challenge, submission, review):
    completed = review.get("evaluation_status") == STATUS_COMPLETED
    attempt = create_project_attempt(
        db,
        {
            "session_id": session_id,
            "challenge_id": stored_challenge.challenge_id,
            "domain": stored_challenge.domain,
            "topic": stored_challenge.topic,
            "difficulty": stored_challenge.difficulty,
            "project_title": stored_challenge.project_title,
            "challenge": challenge,
            "submission": submission,
            "score": review.get("score"),
            "verdict": review.get("verdict", "UNAVAILABLE"),
            "feedback": review.get("feedback", ""),
            "missing_points": review.get("missing_points", ""),
            "improved_approach": review.get("improved_approach", ""),
            "next_steps": review.get("next_steps", ""),
            "architecture_review": review.get("architecture_review", ""),
            "file_findings": review.get("file_findings", []),
            "bugs": review.get("bugs", []),
            "security_issues": review.get("security_issues", []),
            "missing_requirements": review.get("missing_requirements", []),
            "files_reviewed": review.get("files_reviewed", 0),
            "evaluation_status": review.get("evaluation_status", "unavailable"),
            "prompt_version": review.get("prompt_version", ""),
            "model_name": review.get("model", ""),
            "integrity_flags": review.get("integrity_flags", []),
        },
    )
    # Only a completed review consumes the challenge; after an outage the student
    # can resubmit the same challenge.
    if completed:
        mark_project_challenge_completed(
            db,
            session_id=session_id,
            challenge_id=stored_challenge.challenge_id,
        )
    return attempt
