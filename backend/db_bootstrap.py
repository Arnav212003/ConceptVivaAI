"""Bring a local SQLite database to the latest schema on startup.

PostgreSQL deployments run `alembic upgrade head` as an explicit release step and
are never migrated implicitly. For local SQLite we migrate automatically so
existing history survives schema changes:

- no tables yet                         -> `upgrade head`
- tables from the old create_all path   -> `stamp 0001_initial_schema`, then upgrade
- already tracked by Alembic            -> `upgrade head` (no-op when current)
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

from config import settings
from database import DATABASE_URL, engine
from observability import get_logger, log_event

BACKEND_DIR = Path(__file__).resolve().parent
logger = get_logger("db")


def _alembic_config(url: str):
    from alembic.config import Config

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["use_configured_url"] = True
    return config


def migrate_to_head(url: str = DATABASE_URL, bind=None) -> str:
    """Upgrade the database at `url` and return the action taken."""
    from alembic import command

    inspector = inspect(bind or engine)
    tables = set(inspector.get_table_names())
    config = _alembic_config(url)

    if "alembic_version" not in tables and "ml_practice_attempts" in tables:
        command.stamp(config, "0001_initial_schema")
        action = "stamped_legacy_then_upgraded"
    elif not tables:
        action = "created"
    else:
        action = "upgraded"

    command.upgrade(config, "head")
    return action


def bootstrap_database() -> None:
    if not DATABASE_URL.startswith("sqlite") or not settings.auto_migrate_sqlite:
        return
    action = migrate_to_head()
    log_event(logger, "sqlite_schema_ready", action=action)
