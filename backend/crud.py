import json
import secrets

from sqlalchemy import and_, case, func, true

from models import (
    DSAAttempt,
    InterviewReport,
    MLPracticeAttempt,
    ProjectAttempt,
    ProjectChallenge,
)


def _safe_limit_offset(limit=20, offset=0):
    try:
        limit = int(limit)
    except Exception:
        limit = 20

    try:
        offset = int(offset)
    except Exception:
        offset = 0

    if limit < 1:
        limit = 20

    if limit > 100:
        limit = 100

    if offset < 0:
        offset = 0

    return limit, offset


def _normalize_json_for_db(value):
    """Store dict/list/string values as one JSON string."""

    if value is None:
        return json.dumps({}, ensure_ascii=False)

    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)

    if isinstance(value, str):
        clean_value = value.strip()

        if not clean_value:
            return json.dumps({}, ensure_ascii=False)

        try:
            parsed = json.loads(clean_value)

            while isinstance(parsed, str):
                try:
                    parsed = json.loads(parsed)
                except Exception:
                    break

            return json.dumps(parsed, ensure_ascii=False)
        except Exception:
            return json.dumps({"raw": clean_value}, ensure_ascii=False)

    return json.dumps({"value": str(value)}, ensure_ascii=False)


def decode_project_challenge(value):
    """Convert stored challenge_json back to a Python object."""

    if value is None:
        return {}

    if isinstance(value, (dict, list)):
        return value

    if not isinstance(value, str):
        return {"value": str(value)}

    clean_value = value.strip()

    if not clean_value:
        return {}

    try:
        parsed = json.loads(clean_value)

        while isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except Exception:
                break

        return parsed
    except Exception:
        return {"raw": clean_value}


def create_ml_practice_attempt(db, data):
    attempt = MLPracticeAttempt(
        session_id=data.get("session_id"),
        topic=data.get("topic"),
        level=data.get("level"),
        question=data.get("question"),
        answer=data.get("answer"),
        score=data.get("score"),
        verdict=data.get("verdict", "PARTIAL"),
        feedback=data.get("feedback", ""),
        missing_points=data.get("missing_points", ""),
        corrected_answer=data.get("corrected_answer", ""),
        improvement=data.get("improvement", ""),
        evaluation_status=data.get("evaluation_status", "completed"),
        prompt_version=data.get("prompt_version", ""),
        model_name=data.get("model_name", ""),
        integrity_flags=_normalize_json_for_db(data.get("integrity_flags", [])),
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return attempt


def create_interview_report(db, data):
    report = InterviewReport(
        session_id=data.get("session_id"),
        topic=data.get("topic"),
        level=data.get("level"),
        rounds=data.get("rounds", 0),
        average_score=data.get("average_score", 0),
        strong_points=data.get("strong_points", ""),
        weak_points=data.get("weak_points", ""),
        recommendation=data.get("recommendation", ""),
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return report


def create_dsa_attempt(db, data):
    attempt = DSAAttempt(
        session_id=data.get("session_id"),
        mode=data.get("mode", "Practice"),
        topic=data.get("topic"),
        difficulty=data.get("difficulty"),
        problem_name=data.get("problem_name", "DSA Problem"),
        problem=data.get("problem", ""),
        solution=data.get("solution", ""),
        score=data.get("score"),
        status=data.get("status", "Needs Improvement"),
        feedback=data.get("feedback", ""),
        tier=data.get("tier", "ai_generated"),
        evaluation_status=data.get("evaluation_status", "completed"),
        prompt_version=data.get("prompt_version", ""),
        model_name=data.get("model_name", ""),
        integrity_flags=_normalize_json_for_db(data.get("integrity_flags", [])),
        scoring_method=data.get("scoring_method", "ai_rubric"),
        judge_verdict=data.get("judge_verdict", ""),
        judge_submission_id=data.get("judge_submission_id", ""),
        tests_passed=data.get("tests_passed", 0),
        tests_total=data.get("tests_total", 0),
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return attempt


def create_project_challenge(db, data):
    challenge = data.get("challenge", {})
    challenge_id = "pch_" + secrets.token_urlsafe(24)

    project_title = (
        data.get("project_title")
        or challenge.get("project_title")
        or "Project Challenge"
    )

    stored_challenge = ProjectChallenge(
        challenge_id=challenge_id,
        session_id=data.get("session_id"),
        domain=data.get("domain", "Machine Learning"),
        topic=data.get("topic"),
        difficulty=data.get("difficulty", "Beginner"),
        project_title=project_title,
        challenge_json=_normalize_json_for_db(challenge),
        status="ACTIVE",
    )

    db.add(stored_challenge)
    db.commit()
    db.refresh(stored_challenge)

    return stored_challenge


def get_project_challenge_by_id(db, session_id, challenge_id):
    if not challenge_id:
        return None

    return db.query(ProjectChallenge).filter(
        ProjectChallenge.session_id == session_id,
        ProjectChallenge.challenge_id == challenge_id,
        ProjectChallenge.status == "ACTIVE",
    ).first()


def mark_project_challenge_completed(db, session_id, challenge_id):
    if not challenge_id:
        return None

    stored_challenge = db.query(ProjectChallenge).filter(
        ProjectChallenge.session_id == session_id,
        ProjectChallenge.challenge_id == challenge_id,
    ).first()

    if not stored_challenge:
        return None

    stored_challenge.status = "COMPLETED"
    db.commit()
    db.refresh(stored_challenge)

    return stored_challenge


def create_project_attempt(db, data):
    challenge = data.get("challenge", {})

    attempt = ProjectAttempt(
        session_id=data.get("session_id"),
        challenge_id=data.get("challenge_id", ""),
        domain=data.get("domain", "Machine Learning"),
        topic=data.get("topic"),
        difficulty=data.get("difficulty", "Beginner"),
        project_title=data.get("project_title", "Project Challenge"),
        challenge_json=_normalize_json_for_db(challenge),
        submission=data.get("submission", ""),
        score=data.get("score"),
        verdict=data.get("verdict", "PARTIAL"),
        feedback=data.get("feedback", ""),
        missing_points=data.get("missing_points", ""),
        improved_approach=data.get("improved_approach", ""),
        evaluation_status=data.get("evaluation_status", "completed"),
        prompt_version=data.get("prompt_version", ""),
        model_name=data.get("model_name", ""),
        integrity_flags=_normalize_json_for_db(data.get("integrity_flags", [])),
        next_steps=data.get("next_steps", ""),
        architecture_review=data.get("architecture_review", ""),
        file_findings=_normalize_json_for_db(data.get("file_findings", [])),
        bugs=_normalize_json_for_db(data.get("bugs", [])),
        security_issues=_normalize_json_for_db(data.get("security_issues", [])),
        missing_requirements=_normalize_json_for_db(data.get("missing_requirements", [])),
        files_reviewed=data.get("files_reviewed", 0),
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return attempt


def _scored_filter(model):
    """Only completed evaluations with a real score count toward averages."""
    return and_(model.evaluation_status == "completed", model.score.isnot(None))


def _attempt_summary(db, model, session_id, extra_filter=None):
    scored = _scored_filter(model)
    if extra_filter is not None:
        scored = and_(scored, extra_filter)
    count_filter = extra_filter if extra_filter is not None else true()

    total, scored_count, average, unavailable = db.query(
        func.count(case((count_filter, 1))),
        func.count(case((scored, 1))),
        func.avg(case((scored, model.score))),
        func.count(case((and_(count_filter, model.evaluation_status != "completed"), 1))),
    ).filter(model.session_id == session_id).one()

    return {
        "total_attempts": int(total or 0),
        "scored_attempts": int(scored_count or 0),
        "unavailable_attempts": int(unavailable or 0),
        "average_score": round(float(average or 0), 1),
    }


def get_dashboard_stats(db, session_id):
    ml = _attempt_summary(db, MLPracticeAttempt, session_id)
    dsa = _attempt_summary(db, DSAAttempt, session_id)
    dsa_verified = _attempt_summary(db, DSAAttempt, session_id, DSAAttempt.tier == "verified")
    dsa_ai = _attempt_summary(db, DSAAttempt, session_id, DSAAttempt.tier == "ai_generated")
    project = _attempt_summary(db, ProjectAttempt, session_id)

    active_project_challenges = db.query(func.count(ProjectChallenge.id)).filter(
        ProjectChallenge.session_id == session_id,
        ProjectChallenge.status == "ACTIVE",
    ).scalar() or 0

    interview_count, interview_avg = db.query(
        func.count(InterviewReport.id),
        func.avg(InterviewReport.average_score),
    ).filter(InterviewReport.session_id == session_id).one()

    return {
        "session_id": session_id,
        "ml_practice": ml,
        "dsa_practice": {
            **dsa,
            "verified": dsa_verified,
            "ai_generated": dsa_ai,
        },
        "project_challenge": {
            **project,
            "active_challenges": int(active_project_challenges),
        },
        "voice_interview": {
            "total_interviews": int(interview_count or 0),
            "average_score": round(float(interview_avg or 0), 1),
        },
        "overall": {
            "total_activity": ml["total_attempts"] + dsa["total_attempts"]
            + project["total_attempts"] + int(interview_count or 0),
            "unavailable_attempts": ml["unavailable_attempts"] + dsa["unavailable_attempts"]
            + project["unavailable_attempts"],
        },
    }


def get_user_history(db, session_id, limit=20, offset=0):
    limit, offset = _safe_limit_offset(limit, offset)

    ml_attempts = db.query(MLPracticeAttempt).filter(
        MLPracticeAttempt.session_id == session_id
    ).order_by(
        MLPracticeAttempt.created_at.desc()
    ).offset(offset).limit(limit).all()

    dsa_attempts = db.query(DSAAttempt).filter(
        DSAAttempt.session_id == session_id
    ).order_by(
        DSAAttempt.created_at.desc()
    ).offset(offset).limit(limit).all()

    project_attempts = db.query(ProjectAttempt).filter(
        ProjectAttempt.session_id == session_id
    ).order_by(
        ProjectAttempt.created_at.desc()
    ).offset(offset).limit(limit).all()

    interview_reports = db.query(InterviewReport).filter(
        InterviewReport.session_id == session_id
    ).order_by(
        InterviewReport.created_at.desc()
    ).offset(offset).limit(limit).all()

    return {
        "ml_practice": ml_attempts,
        "dsa_practice": dsa_attempts,
        "project_challenge": project_attempts,
        "voice_interview": interview_reports,
        "pagination": {
            "limit": limit,
            "offset": offset,
        },
    }
