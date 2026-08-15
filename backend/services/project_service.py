"""Business logic for AI-generated project challenges and their evaluation."""
import json

from config import GEMINI_API_KEY
from crud import create_project_attempt, mark_project_challenge_completed
from services.gemini_client import client
from utils import extract_json


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
    }


def generate_project_challenge_with_gemini(domain, topic, difficulty):
    if not GEMINI_API_KEY or not client:
        return get_fallback_project_challenge(domain, topic, difficulty)

    prompt = f"""
You are ConceptVivaAI, an AI assessment platform.

Generate a project-based challenge for a student.

Domain: {domain}
Topic: {topic}
Difficulty: {difficulty}

The challenge should be practical, beginner-friendly if difficulty is Beginner,
and should feel like a mini hackathon/project assignment.

Return only valid JSON in this exact format:
{{
  "project_title": "clear project title",
  "domain": "{domain}",
  "topic": "{topic}",
  "difficulty": "{difficulty}",
  "problem_statement": "detailed but simple problem statement",
  "dataset_columns": [
    {{
      "column": "column_name",
      "description": "what this column means"
    }}
  ],
  "tasks": [
    "task 1",
    "task 2",
    "task 3"
  ],
  "evaluation_metrics": [
    "metric or evaluation point 1",
    "metric or evaluation point 2"
  ],
  "hints": [
    "hint 1",
    "hint 2"
  ],
  "submission_checklist": [
    "checklist item 1",
    "checklist item 2"
  ]
}}

Rules:
1. Stay strictly inside the selected topic.
2. Do not give the full solution.
3. Do not provide complete code.
4. Give a dataset/table schema.
5. Make it useful for portfolio/project practice.
6. Keep it clear for students.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        result = extract_json(response.text)

        if not result:
            return get_fallback_project_challenge(domain, topic, difficulty)

        result.setdefault("project_title", f"{topic} Mini Project Challenge")
        result.setdefault("domain", domain)
        result.setdefault("topic", topic)
        result.setdefault("difficulty", difficulty)
        result.setdefault("problem_statement", "Project problem statement not available.")
        result.setdefault("dataset_columns", [])
        result.setdefault("tasks", [])
        result.setdefault("evaluation_metrics", [])
        result.setdefault("hints", [])
        result.setdefault("submission_checklist", [])

        return result

    except Exception:
        return get_fallback_project_challenge(domain, topic, difficulty)


def _project_file_bundle(project_files):
    """Create a clear, bounded file-by-file source bundle for Gemini (and for
    persistence — this is also what gets stored as `submission`, so the
    actual submitted code isn't discarded after evaluation)."""
    sections = []
    for item in project_files or []:
        path = str(item.get("path", "")).strip()
        content = str(item.get("content", ""))
        if not path:
            continue
        sections.append(f"\n===== FILE: {path} =====\n{content}\n===== END FILE: {path} =====")
    return "\n".join(sections)


def build_full_source_bundle(project_files):
    """Public wrapper: the actual submitted source code, concatenated with
    file markers. Used both for the Gemini review prompt and for what gets
    persisted as `submission`, so the original code isn't discarded."""
    return _project_file_bundle(project_files)


def build_project_submission_manifest(project_files, project_notes=""):
    """Short human-readable summary (file list + notes) used in messages and
    as a fallback when there's no bundled source to show."""
    files = project_files or []
    lines = [f"Full project source submitted: {len(files)} files"]
    for item in files:
        path = str(item.get("path", "unknown"))
        content = str(item.get("content", ""))
        lines.append(f"- {path} ({len(content)} characters)")
    if project_notes.strip():
        lines.append("\nStudent notes:\n" + project_notes.strip())
    return "\n".join(lines)


def evaluate_project_submission_with_gemini(
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
        return {
            "score": 0,
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
        }

    if not GEMINI_API_KEY or not client:
        return {
            "score": 6,
            "verdict": "PARTIAL",
            "feedback": f"Your full project submission ({file_count or 1} source unit(s)) was received. Gemini API is unavailable right now, so detailed code review could not run.",
            "missing_points": "Detailed cross-file AI review is unavailable until Gemini is configured.",
            "improved_approach": "Configure Gemini, then resubmit the complete source folder for file-by-file and cross-file analysis.",
            "next_steps": "Set GEMINI_API_KEY and retry the project review.",
            "suggested_resources": [],
            "architecture_review": "Could not evaluate architecture without Gemini.",
            "file_findings": [],
            "bugs": [],
            "security_issues": [],
            "missing_requirements": [],
            "files_reviewed": file_count,
        }

    prompt = f"""
You are ConceptVivaAI, a strict senior software engineer and project evaluator.

Evaluate the student's COMPLETE project source submission against the assigned challenge.
Do a real cross-file code review, not a generic project-description review.

Domain:
{domain}

Topic:
{topic}

Difficulty:
{difficulty}

Project Challenge:
{json.dumps(challenge, indent=2)}

Student Notes:
{project_notes or "No additional notes."}

Complete Project Source ({file_count if file_count else "legacy text submission"}):
{source_for_review}

Review requirements:
1. Check whether the implementation actually satisfies the project challenge.
2. Understand the project structure and how files/modules connect.
3. Point out concrete bugs and incorrect logic, naming the exact file whenever possible.
4. Check missing requirements, incomplete features, dead code, error handling and edge cases.
5. Check architecture, APIs, database/data flow, model pipeline or algorithm choices where relevant.
6. Check security and unsafe patterns where relevant. Do not invent vulnerabilities.
7. Distinguish build/runtime blockers from minor improvements.
8. Give actionable fixes, but do not rewrite the student's whole project.
9. Base the score on submitted code, not on how polished the explanation sounds.

Return only valid JSON in this exact shape:
{{
  "score": 0,
  "verdict": "STRONG or PARTIAL or WEAK",
  "feedback": "overall conclusion grounded in the submitted code",
  "architecture_review": "how the project is structured and whether the design is appropriate",
  "file_findings": [
    {{
      "file": "relative/path/to/file",
      "status": "GOOD or ISSUE or REVIEW",
      "issues": ["specific issue"],
      "suggestions": ["specific improvement"]
    }}
  ],
  "bugs": [
    {{
      "severity": "CRITICAL or HIGH or MEDIUM or LOW",
      "file": "relative/path/to/file",
      "issue": "what is wrong",
      "fix": "how to fix it"
    }}
  ],
  "security_issues": [
    {{
      "severity": "HIGH or MEDIUM or LOW",
      "file": "relative/path/to/file",
      "issue": "security issue",
      "fix": "safe fix"
    }}
  ],
  "missing_requirements": ["challenge requirement that is missing or incomplete"],
  "missing_points": "short summary of the most important missing technical points",
  "improved_approach": "recommended architecture/implementation improvements in priority order",
  "next_steps": "what the student should fix next",
  "suggested_resources": ["topic/resource to revise"]
}}

Scoring guide:
0-2: empty, unrelated, or fundamentally non-working submission.
3-4: major parts missing or core implementation is incorrect.
5-6: basic implementation exists but important requirements/bugs remain.
7-8: good working project with limited issues or missing polish.
9-10: strong, complete, technically sound, portfolio-ready implementation.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        result = extract_json(response.text)
        if not result:
            raise ValueError("Gemini did not return valid project-review JSON")

        result.setdefault("score", 6)
        result.setdefault("verdict", "PARTIAL")
        result.setdefault("feedback", "Project source reviewed.")
        result.setdefault("architecture_review", "Architecture review not provided.")
        result.setdefault("file_findings", [])
        result.setdefault("bugs", [])
        result.setdefault("security_issues", [])
        result.setdefault("missing_requirements", [])
        result.setdefault("missing_points", "No additional missing points provided.")
        result.setdefault("improved_approach", "Keep the implementation modular and test the complete flow.")
        result.setdefault("next_steps", "Fix the highest-severity findings and resubmit.")
        result.setdefault("suggested_resources", [])
        result["files_reviewed"] = file_count
        return result
    except Exception:
        return {
            "score": 6,
            "verdict": "PARTIAL",
            "feedback": "Gemini could not complete the full source-code review on this request.",
            "missing_points": "Detailed file-level findings could not be generated.",
            "improved_approach": "Verify Gemini configuration and resubmit the complete source folder.",
            "next_steps": "Retry the review after checking the backend/Gemini connection.",
            "suggested_resources": [],
            "architecture_review": "Could not complete architecture review.",
            "file_findings": [],
            "bugs": [],
            "security_issues": [],
            "missing_requirements": [],
            "files_reviewed": file_count,
        }


def normalize_project_review(review):
    review = dict(review or {})
    try:
        score = max(0.0, min(10.0, float(review.get("score", 5))))
    except Exception:
        score = 5.0
    review["score"] = score
    review["verdict"] = "STRONG" if score >= 8 else ("PARTIAL" if score >= 5 else "WEAK")
    review.setdefault("feedback", "Project review completed.")
    review.setdefault("missing_points", "Add clearer technical details and evaluation evidence.")
    review.setdefault("improved_approach", "Use a structured problem-to-evaluation workflow.")
    review.setdefault("next_steps", "Improve the weak areas and resubmit.")
    review.setdefault("suggested_resources", [])
    review.setdefault("architecture_review", "Architecture review not provided.")
    review.setdefault("file_findings", [])
    review.setdefault("bugs", [])
    review.setdefault("security_issues", [])
    review.setdefault("missing_requirements", [])
    review.setdefault("files_reviewed", 0)
    return review


def save_verified_project_attempt(db, session_id, stored_challenge, challenge, submission, review):
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
            "score": review.get("score", 0),
            "verdict": review.get("verdict", "PARTIAL"),
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
        },
    )
    mark_project_challenge_completed(
        db,
        session_id=session_id,
        challenge_id=stored_challenge.challenge_id,
    )
    return attempt
