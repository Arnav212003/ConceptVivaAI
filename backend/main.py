"""FastAPI app setup for ConceptVivaAI."""
import hmac
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db_bootstrap import bootstrap_database
from observability import (
    RequestContextMiddleware,
    configure_logging,
    get_logger,
    log_event,
    metrics_response,
)
from routes.analytics_routes import router as analytics_router
from routes.auth_routes import router as auth_router
from routes.dashboard_routes import router as dashboard_router
from routes.dsa_routes import router as dsa_router
from routes.interview_routes import router as interview_router
from routes.ml_routes import router as ml_router
from routes.project_routes import router as project_router
from routes.session_routes import router as session_router
from routes.translate_routes import router as translate_router
from services import llm

configure_logging()
logger = get_logger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    bootstrap_database()
    if os.getenv("ENABLE_CODE_EXECUTION"):
        log_event(logger, "deprecated_setting_ignored", level=30, setting="ENABLE_CODE_EXECUTION",
                  replacement="JUDGE_ENABLED with an isolated executor")
    log_event(logger, "startup", environment=settings.environment,
              llm_configured=settings.llm_configured, redis=bool(settings.redis_url))
    yield


app = FastAPI(title="ConceptVivaAI Backend", lifespan=lifespan)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Session-Id", "X-Session-Token", "X-CSRF-Token", "X-Request-ID"],
    expose_headers=["X-Request-ID", "Retry-After"],
)

app.include_router(session_router)
app.include_router(auth_router)
app.include_router(dsa_router)
app.include_router(interview_router)
app.include_router(ml_router)
app.include_router(project_router)
app.include_router(dashboard_router)
app.include_router(translate_router)
app.include_router(analytics_router)


@app.get("/")
def home():
    return {
        "message": "ConceptVivaAI Python FastAPI backend is running"
    }


@app.get("/health")
def health():
    """Liveness plus dependency summary. Never includes secrets or URLs."""
    return {
        "status": "ok",
        "llm": {"configured": settings.llm_configured, "circuit": llm.breaker.state},
        "redis": {"configured": bool(settings.redis_url)},
    }


@app.get("/metrics", include_in_schema=False)
def metrics(authorization: str = Header(default="")):
    # Metrics are internal. With METRICS_TOKEN set, require `Authorization: Bearer <token>`.
    if settings.metrics_token:
        expected = f"Bearer {settings.metrics_token}"
        if not hmac.compare_digest(authorization.encode(), expected.encode()):
            raise HTTPException(status_code=401, detail="Metrics token required.")
    elif settings.environment == "production":
        raise HTTPException(status_code=404, detail="Not found")
    return metrics_response()
