import json
import secrets

from sqlalchemy import func

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
    """
    Stores JSON safely as a single JSON string.

    Handles:
    - dict/list from frontend
    - JSON string from frontend
    - already double-encoded JSON string
    - invalid string fallback
    """

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
    """
    Converts stored challenge_json back to object.
    Also fixes old double-encoded rows while reading.
    """

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
        score=data.get("score", 0),
        verdict=data.get("verdict", "PARTIAL"),
        feedback=data.get("feedback", ""),
        missing_points=data.get("missing_points", ""),
        corrected_answer=data.get("corrected_answer", ""),
        improvement=data.get("improvement", ""),
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
        score=data.get("score", 0),
        status=data.get("status", "Needs Improvement"),
        feedback=data.get("feedback", ""),
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


def create_project_attempt(db, data):
    challenge = data.get("challenge", {})

    attempt = ProjectAttempt(
        session_id=data.get("session_id"),
        domain=data.get("domain", "Machine Learning"),
        topic=data.get("topic"),
        difficulty=data.get("difficulty", "Beginner"),
        project_title=data.get("project_title", "Project Challenge"),
        challenge_json=_normalize_json_for_db(challenge),
        submission=data.get("submission", ""),
        score=data.get("score", 0),
        verdict=data.get("verdict", "PARTIAL"),
        feedback=data.get("feedback", ""),
        missing_points=data.get("missing_points", ""),
        improved_approach=data.get("improved_approach", ""),
        next_steps=data.get("next_steps", ""),
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return attempt


def get_dashboard_stats(db, session_id):
    ml_count = db.query(MLPracticeAttempt).filter(
        MLPracticeAttempt.session_id == session_id
    ).count()

    dsa_count = db.query(DSAAttempt).filter(
        DSAAttempt.session_id == session_id
    ).count()

    project_count = db.query(ProjectAttempt).filter(
        ProjectAttempt.session_id == session_id
    ).count()

    interview_count = db.query(InterviewReport).filter(
        InterviewReport.session_id == session_id
    ).count()

    active_project_challenges = db.query(ProjectChallenge).filter(
        ProjectChallenge.session_id == session_id,
        ProjectChallenge.status == "ACTIVE",
    ).count()

    ml_avg = db.query(func.avg(MLPracticeAttempt.score)).filter(
        MLPracticeAttempt.session_id == session_id
    ).scalar() or 0

    dsa_avg = db.query(func.avg(DSAAttempt.score)).filter(
        DSAAttempt.session_id == session_id
    ).scalar() or 0

    project_avg = db.query(func.avg(ProjectAttempt.score)).filter(
        ProjectAttempt.session_id == session_id
    ).scalar() or 0

    interview_avg = db.query(func.avg(InterviewReport.average_score)).filter(
        InterviewReport.session_id == session_id
    ).scalar() or 0

    return {
        "session_id": session_id,
        "ml_practice": {
            "total_attempts": ml_count,
            "average_score": round(float(ml_avg), 1),
        },
        "dsa_practice": {
            "total_attempts": dsa_count,
            "average_score": round(float(dsa_avg), 1),
        },
        "project_challenge": {
            "total_attempts": project_count,
            "active_challenges": active_project_challenges,
            "average_score": round(float(project_avg), 1),
        },
        "voice_interview": {
            "total_interviews": interview_count,
            "average_score": round(float(interview_avg), 1),
        },
        "overall": {
            "total_activity": ml_count + dsa_count + project_count + interview_count,
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