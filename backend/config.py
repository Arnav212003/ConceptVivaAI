"""Single source of truth for backend configuration.

Environment files are loaded once here (root `.env.local`, then `backend/.env`).
Every other module reads settings from this file instead of calling `os.getenv`
or `load_dotenv` on its own, so defaults and validation live in one place.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env.local")
load_dotenv(BASE_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_list(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    environment: str
    log_level: str

    # Gemini / LLM gateway
    gemini_api_key: str
    gemini_model: str
    llm_timeout_seconds: float
    llm_max_retries: int
    llm_backoff_base_seconds: float
    llm_breaker_failure_threshold: int
    llm_breaker_reset_seconds: float

    # Sessions and receipts
    session_secret_key: str
    session_ttl_seconds: int
    evaluation_receipt_ttl_seconds: int

    # Database
    database_url: str
    auto_migrate_sqlite: bool

    # HTTP
    frontend_url: str
    cors_origins: list[str]

    # Redis (rate limiting, judge queue, cache). Empty = in-process fallbacks.
    redis_url: str

    # Rate limits
    disable_rate_limiting: bool
    ai_requests_per_minute: int
    general_requests_per_minute: int
    session_starts_per_minute: int

    # Code judge
    judge_enabled: bool
    judge_executor: str
    judge0_url: str
    judge0_api_key: str
    judge0_python_language_id: int
    judge0_daily_limit: int
    sandbox_url: str
    sandbox_shared_secret: str
    judge_allow_unsafe_local: bool
    judge_wait_seconds: float
    judge_cpu_seconds: float
    judge_wall_seconds: float
    judge_memory_mb: int
    judge_max_processes: int
    judge_max_output_bytes: int

    # Google OAuth + cookie auth
    google_client_id: str
    google_client_secret: str
    oauth_redirect_uri: str
    auth_session_ttl_seconds: int
    cookie_secure: bool

    # Observability and analytics
    metrics_token: str
    analytics_admin_token: str

    extra: dict = field(default_factory=dict)

    @property
    def llm_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def google_oauth_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret and self.oauth_redirect_uri)


def _build_cors_origins(frontend_url: str) -> list[str]:
    origins = _env_list("CORS_ORIGINS") or [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    if frontend_url and frontend_url not in origins:
        origins.append(frontend_url)
    return origins


def load_settings() -> Settings:
    session_secret_key = _env("SESSION_SECRET_KEY")
    if not session_secret_key:
        raise RuntimeError(
            "SESSION_SECRET_KEY is missing. Add SESSION_SECRET_KEY in .env.local before running backend."
        )

    frontend_url = _env("FRONTEND_URL", "http://localhost:3000")
    environment = _env("APP_ENV", "development").lower()

    return Settings(
        environment=environment,
        log_level=_env("LOG_LEVEL", "INFO").upper(),
        gemini_api_key=_env("GEMINI_API_KEY"),
        gemini_model=_env("GEMINI_MODEL", "gemini-2.5-flash"),
        llm_timeout_seconds=_env_float("LLM_TIMEOUT_SECONDS", 45.0),
        llm_max_retries=max(0, _env_int("LLM_MAX_RETRIES", 2)),
        llm_backoff_base_seconds=_env_float("LLM_BACKOFF_BASE_SECONDS", 0.5),
        llm_breaker_failure_threshold=max(1, _env_int("LLM_BREAKER_FAILURE_THRESHOLD", 5)),
        llm_breaker_reset_seconds=_env_float("LLM_BREAKER_RESET_SECONDS", 30.0),
        session_secret_key=session_secret_key,
        session_ttl_seconds=_env_int("SESSION_TTL_SECONDS", 60 * 60 * 24 * 30),
        evaluation_receipt_ttl_seconds=_env_int("EVALUATION_RECEIPT_TTL_SECONDS", 60 * 60 * 6),
        database_url=_env("DATABASE_URL", "sqlite:///./conceptviva.db"),
        auto_migrate_sqlite=_env_bool("AUTO_MIGRATE_SQLITE", True),
        frontend_url=frontend_url,
        cors_origins=_build_cors_origins(frontend_url),
        redis_url=_env("REDIS_URL"),
        disable_rate_limiting=_env_bool("DISABLE_RATE_LIMITING", False),
        ai_requests_per_minute=_env_int("AI_REQUESTS_PER_MINUTE", 20),
        general_requests_per_minute=_env_int("GENERAL_REQUESTS_PER_MINUTE", 120),
        session_starts_per_minute=_env_int("SESSION_STARTS_PER_MINUTE", 20),
        judge_enabled=_env_bool("JUDGE_ENABLED", False),
        judge_executor=_env("JUDGE_EXECUTOR", "judge0").lower(),
        judge0_url=_env("JUDGE0_URL").rstrip("/"),
        judge0_api_key=_env("JUDGE0_API_KEY"),
        judge0_python_language_id=_env_int("JUDGE0_PYTHON_LANGUAGE_ID", 71),
        # 0 means no limit. RapidAPI's free plan allows 50 requests a day.
        judge0_daily_limit=_env_int("JUDGE0_DAILY_LIMIT", 0),
        sandbox_url=_env("SANDBOX_URL").rstrip("/"),
        sandbox_shared_secret=_env("SANDBOX_SHARED_SECRET"),
        judge_allow_unsafe_local=_env_bool("JUDGE_ALLOW_UNSAFE_LOCAL", False),
        judge_wait_seconds=_env_float("JUDGE_WAIT_SECONDS", 15.0),
        judge_cpu_seconds=_env_float("JUDGE_CPU_SECONDS", 2.0),
        judge_wall_seconds=_env_float("JUDGE_WALL_SECONDS", 5.0),
        judge_memory_mb=_env_int("JUDGE_MEMORY_MB", 256),
        judge_max_processes=_env_int("JUDGE_MAX_PROCESSES", 16),
        judge_max_output_bytes=_env_int("JUDGE_MAX_OUTPUT_BYTES", 256_000),
        google_client_id=_env("GOOGLE_CLIENT_ID"),
        google_client_secret=_env("GOOGLE_CLIENT_SECRET"),
        oauth_redirect_uri=_env("OAUTH_REDIRECT_URI"),
        auth_session_ttl_seconds=_env_int("AUTH_SESSION_TTL_SECONDS", 60 * 60 * 24 * 14),
        cookie_secure=_env_bool("COOKIE_SECURE", environment == "production"),
        metrics_token=_env("METRICS_TOKEN"),
        analytics_admin_token=_env("ANALYTICS_ADMIN_TOKEN"),
    )


settings = load_settings()

# Backward-compatible aliases for modules that still import constants.
GEMINI_API_KEY = settings.gemini_api_key
FRONTEND_URL = settings.frontend_url
