"""Privacy-conscious analytics and per-user progress.

Product analytics (`record_event`):
- Only aggregate daily counters (day, event, dimension, count) are stored.
- Event names and dimensions come from fixed allowlists; anything else is dropped,
  so free text, ids or URLs with query strings can never be stored.
- Browsers that send `DNT: 1` or `Sec-GPC: 1` are not counted at all.

Personal progress (`progress_for_owner`) is computed from the user's own history
rows on demand; it needs no extra tracking.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import AnalyticsDaily, DSAAttempt, InterviewReport, MLPracticeAttempt, ProjectAttempt

PAGE_ROUTES = {
    "/", "/ml", "/ml/practice", "/ml/interview", "/ml/project",
    "/dsa", "/dsa/practice", "/dsa/mock", "/dsa/history", "/dashboard",
}
EVENTS = {
    "page_view": PAGE_ROUTES,
    "practice_started": {"ml_practice", "dsa_practice", "dsa_mock", "voice_interview", "project_challenge"},
    "attempt_submitted": {"ml_practice", "dsa_practice", "dsa_mock", "voice_interview", "project_challenge"},
    "solution_revealed": {"dsa_practice"},
    "sign_in": {"google"},
}
MAX_SUMMARY_DAYS = 90


def tracking_allowed(headers) -> bool:
    return headers.get("dnt") != "1" and headers.get("sec-gpc") != "1"


def normalize(event: str, dimension: str) -> tuple[str, str] | None:
    allowed = EVENTS.get(event)
    if allowed is None or dimension not in allowed:
        return None
    return event, dimension


def record_event(db: Session, event: str, dimension: str, today: date | None = None) -> bool:
    normalized = normalize(event, dimension)
    if normalized is None:
        return False
    day = (today or datetime.now(timezone.utc).date()).isoformat()
    updated = db.query(AnalyticsDaily).filter(
        AnalyticsDaily.day == day, AnalyticsDaily.event == event, AnalyticsDaily.dimension == dimension
    ).update({AnalyticsDaily.count: AnalyticsDaily.count + 1}, synchronize_session=False)
    if not updated:
        db.add(AnalyticsDaily(day=day, event=event, dimension=dimension, count=1))
        try:
            db.commit()
            return True
        except IntegrityError:  # another request created the row first
            db.rollback()
            db.query(AnalyticsDaily).filter(
                AnalyticsDaily.day == day, AnalyticsDaily.event == event, AnalyticsDaily.dimension == dimension
            ).update({AnalyticsDaily.count: AnalyticsDaily.count + 1}, synchronize_session=False)
    db.commit()
    return True


def summary(db: Session, days: int = 30) -> dict:
    days = max(1, min(days, MAX_SUMMARY_DAYS))
    since = (datetime.now(timezone.utc).date() - timedelta(days=days - 1)).isoformat()
    rows = db.query(AnalyticsDaily.event, AnalyticsDaily.dimension, func.sum(AnalyticsDaily.count)).filter(
        AnalyticsDaily.day >= since
    ).group_by(AnalyticsDaily.event, AnalyticsDaily.dimension).all()
    totals: dict = defaultdict(dict)
    for event, dimension, count in rows:
        totals[event][dimension] = int(count or 0)
    daily = db.query(AnalyticsDaily.day, func.sum(AnalyticsDaily.count)).filter(
        AnalyticsDaily.day >= since, AnalyticsDaily.event == "attempt_submitted"
    ).group_by(AnalyticsDaily.day).order_by(AnalyticsDaily.day).all()
    return {
        "since": since,
        "days": days,
        "totals": totals,
        "attempts_per_day": [{"day": day, "count": int(count or 0)} for day, count in daily],
    }


def _as_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).date()
    return None


def progress_for_owner(db: Session, owner_id: str, weeks: int = 8, today: date | None = None) -> dict:
    """Streak, weekly activity and weekly average score from the owner's own rows."""
    today = today or datetime.now(timezone.utc).date()
    start = today - timedelta(weeks=weeks)
    activity_days: set[date] = set()
    weekly = defaultdict(lambda: {"attempts": 0, "scored": 0, "score_total": 0.0})

    sources = [
        (MLPracticeAttempt, MLPracticeAttempt.score, True),
        (DSAAttempt, DSAAttempt.score, True),
        (ProjectAttempt, ProjectAttempt.score, True),
        (InterviewReport, InterviewReport.average_score, False),
    ]
    for model, score_column, has_status in sources:
        columns = [model.created_at, score_column]
        if has_status:
            columns.append(model.evaluation_status)
        for row in db.query(*columns).filter(model.session_id == owner_id).all():
            day = _as_date(row[0])
            if day is None:
                continue
            activity_days.add(day)
            if day < start:
                continue
            week = (day - timedelta(days=day.weekday())).isoformat()
            weekly[week]["attempts"] += 1
            completed = row[2] == "completed" if has_status else True
            if completed and row[1] is not None:
                weekly[week]["scored"] += 1
                weekly[week]["score_total"] += float(row[1])

    streak = 0
    cursor = today if today in activity_days else today - timedelta(days=1)
    while cursor in activity_days:
        streak += 1
        cursor -= timedelta(days=1)

    weeks_out = []
    for offset in range(weeks - 1, -1, -1):
        monday = today - timedelta(days=today.weekday()) - timedelta(weeks=offset)
        data = weekly.get(monday.isoformat(), {"attempts": 0, "scored": 0, "score_total": 0.0})
        weeks_out.append({
            "week_start": monday.isoformat(),
            "attempts": data["attempts"],
            "average_score": round(data["score_total"] / data["scored"], 1) if data["scored"] else None,
        })

    return {
        "current_streak_days": streak,
        "active_days_last_30": sum(1 for day in activity_days if day > today - timedelta(days=30)),
        "weeks": weeks_out,
    }
