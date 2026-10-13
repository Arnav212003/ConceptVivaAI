import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env.local")
load_dotenv(BASE_DIR / ".env")


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./conceptviva.db")


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)

    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)

    return url


DATABASE_URL = normalize_database_url(DATABASE_URL)

connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False
    }


engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=not DATABASE_URL.startswith("sqlite"),
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
