from crud import create_ml_practice_attempt, get_dashboard_stats
from database import SessionLocal, normalize_database_url


def test_sqlite_database_url_is_unchanged():
    assert normalize_database_url("sqlite:///./conceptviva.db") == "sqlite:///./conceptviva.db"


def test_postgresql_database_url_uses_psycopg2_driver():
    result = normalize_database_url(
        "postgresql://username:password@host:5432/database_name"
    )

    assert result == "postgresql+psycopg2://username:password@host:5432/database_name"


def test_postgresql_psycopg2_database_url_is_unchanged():
    url = "postgresql+psycopg2://username:password@host:5432/database_name"

    assert normalize_database_url(url) == url


def test_basic_ml_attempt_updates_dashboard_stats(client):
    session_response = client.post("/session/start")
    session_id = session_response.json()["session_id"]

    db = SessionLocal()
    try:
        create_ml_practice_attempt(
            db,
            {
                "session_id": session_id,
                "topic": "KNN",
                "level": "Easy",
                "question": "What is KNN?",
                "answer": "A supervised learning algorithm.",
                "score": 8,
                "verdict": "STRONG",
            },
        )
        stats = get_dashboard_stats(db, session_id)
    finally:
        db.close()

    assert stats["ml_practice"]["total_attempts"] == 1
    assert stats["ml_practice"]["average_score"] == 8.0
