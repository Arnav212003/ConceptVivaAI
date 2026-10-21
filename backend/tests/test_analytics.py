"""Privacy-conscious analytics and per-user progress."""
from datetime import date, datetime, timedelta, timezone

import analytics
from database import SessionLocal
from models import AnalyticsDaily, MLPracticeAttempt
from tests.test_api_flows import start_test_session


def test_allowlisted_events_are_counted_as_daily_aggregates(client):
    for _ in range(3):
        assert client.post("/analytics/event", json={"event": "page_view", "dimension": "/dashboard"}).json() == {
            "recorded": True
        }
    db = SessionLocal()
    try:
        rows = db.query(AnalyticsDaily).all()
    finally:
        db.close()
    assert len(rows) == 1
    assert (rows[0].event, rows[0].dimension, rows[0].count) == ("page_view", "/dashboard", 3)
    # The table has no column that could hold an identity.
    assert set(AnalyticsDaily.__table__.columns.keys()) == {"id", "day", "event", "dimension", "count"}


def test_unknown_events_and_free_text_are_dropped(client):
    for payload in (
        {"event": "page_view", "dimension": "/dashboard?email=a@b.com"},
        {"event": "keystrokes", "dimension": "x"},
        {"event": "attempt_submitted", "dimension": "student@example.com"},
    ):
        assert client.post("/analytics/event", json=payload).json() == {"recorded": False}


def test_do_not_track_and_gpc_are_respected(client):
    for header in ({"DNT": "1"}, {"Sec-GPC": "1"}):
        response = client.post("/analytics/event", headers=header, json={"event": "page_view", "dimension": "/"})
        assert response.json() == {"recorded": False, "reason": "do_not_track"}


def test_summary_requires_admin_token(client, override_settings):
    assert client.get("/analytics/summary").status_code == 404
    override_settings(analytics_admin_token="admin-secret")
    assert client.get("/analytics/summary").status_code == 401
    client.post("/analytics/event", json={"event": "attempt_submitted", "dimension": "dsa_practice"})
    data = client.get("/analytics/summary", headers={"Authorization": "Bearer admin-secret"}).json()
    assert data["totals"]["attempt_submitted"]["dsa_practice"] == 1
    assert data["attempts_per_day"][0]["count"] == 1


def test_progress_streak_and_weekly_scores_ignore_unscored_attempts():
    today = date(2026, 10, 21)
    db = SessionLocal()
    try:
        from models import Base
        from database import engine

        Base.metadata.create_all(bind=engine)
        db.query(MLPracticeAttempt).filter(MLPracticeAttempt.session_id == "usr_progress").delete()
        for days_ago, score, status in ((0, 8.0, "completed"), (1, None, "unavailable"), (2, 6.0, "completed"), (5, 9.0, "completed")):
            created = datetime.combine(today - timedelta(days=days_ago), datetime.min.time(), tzinfo=timezone.utc)
            db.add(MLPracticeAttempt(session_id="usr_progress", topic="KNN", level="Easy", question="q", answer="a",
                                     score=score, evaluation_status=status, created_at=created))
        db.commit()
        progress = analytics.progress_for_owner(db, "usr_progress", weeks=2, today=today)
    finally:
        db.close()

    assert progress["current_streak_days"] == 3  # today, yesterday (unscored still counts as activity), 2 days ago
    this_week = progress["weeks"][-1]
    assert this_week["week_start"] == "2026-10-19"
    assert this_week["attempts"] == 3
    assert this_week["average_score"] == 7.0  # (8 + 6) / 2, the unavailable attempt is excluded
    assert progress["weeks"][0]["average_score"] == 9.0


def test_progress_endpoint_uses_the_callers_own_history(client):
    _, headers = start_test_session(client)
    data = client.get("/progress", headers=headers).json()
    assert data["current_streak_days"] == 0
    assert len(data["weeks"]) == 8
