"""Alembic migrations apply cleanly and preserve existing history."""
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, inspect

import db_bootstrap


def _url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_fresh_database_upgrades_to_head(tmp_path):
    db_path = tmp_path / "fresh.db"
    engine = create_engine(_url(db_path))
    assert db_bootstrap.migrate_to_head(_url(db_path), bind=engine) == "created"

    columns = {c["name"] for c in inspect(engine).get_columns("ml_practice_attempts")}
    assert {"evaluation_status", "prompt_version", "model_name", "integrity_flags"} <= columns


def test_existing_0001_database_keeps_rows_and_marks_them_completed(tmp_path):
    from alembic import command

    db_path = tmp_path / "legacy.db"
    url = _url(db_path)
    command.upgrade(db_bootstrap._alembic_config(url), "0001_initial_schema")

    con = sqlite3.connect(db_path)
    con.execute(
        "insert into dsa_attempts (session_id, mode, topic, difficulty, problem_name, score, status, tier) "
        "values ('cv_old', 'Practice', 'Arrays', 'Easy', 'Two Sum', 7.5, 'Needs Improvement', 'ai_generated')"
    )
    con.commit()
    con.close()

    engine = create_engine(url)
    assert db_bootstrap.migrate_to_head(url, bind=engine) == "upgraded"

    con = sqlite3.connect(db_path)
    row = con.execute("select score, evaluation_status from dsa_attempts where session_id='cv_old'").fetchone()
    con.close()
    assert row == (7.5, "completed")


def test_unstamped_create_all_database_is_stamped_then_upgraded(tmp_path):
    db_path = tmp_path / "unstamped.db"
    url = _url(db_path)
    # Recreate the shape the old `Base.metadata.create_all` produced, without alembic_version.
    from alembic import command

    command.upgrade(db_bootstrap._alembic_config(url), "0001_initial_schema")
    con = sqlite3.connect(db_path)
    con.execute("drop table alembic_version")
    con.commit()
    con.close()

    engine = create_engine(url)
    assert db_bootstrap.migrate_to_head(url, bind=engine) == "stamped_legacy_then_upgraded"
    assert "evaluation_status" in {c["name"] for c in inspect(engine).get_columns("project_attempts")}


def test_downgrade_round_trip(tmp_path):
    from alembic import command

    db_path = tmp_path / "roundtrip.db"
    url = _url(db_path)
    config = db_bootstrap._alembic_config(url)
    command.upgrade(config, "head")
    command.downgrade(config, "0001_initial_schema")
    engine = create_engine(url)
    assert "evaluation_status" not in {c["name"] for c in inspect(engine).get_columns("dsa_attempts")}
    command.upgrade(config, "head")
