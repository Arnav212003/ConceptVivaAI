"""FastAPI app setup for ConceptVivaAI."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import FRONTEND_URL
from database import Base, DATABASE_URL, engine

from routes.dashboard_routes import router as dashboard_router
from routes.dsa_routes import router as dsa_router
from routes.interview_routes import router as interview_router
from routes.ml_routes import router as ml_router
from routes.project_routes import router as project_router
from routes.session_routes import router as session_router
from routes.translate_routes import router as translate_router

# Some older tests import this helper from main.py.
from services.dsa_service import run_python_tests  # noqa: F401

app = FastAPI(title="ConceptVivaAI Backend")

# SQLite fallback for first-time local runs.
if DATABASE_URL.startswith("sqlite"):
    Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.29.17:3000",
        FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_router)
app.include_router(dsa_router)
app.include_router(interview_router)
app.include_router(ml_router)
app.include_router(project_router)
app.include_router(dashboard_router)
app.include_router(translate_router)


@app.get("/")
def home():
    return {
        "message": "ConceptVivaAI Python FastAPI backend is running"
    }
