import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


TEST_DB_PATH = Path(__file__).resolve().parent / "conceptviva_test.db"

os.environ["SESSION_SECRET_KEY"] = "test_secret_key_for_unit_tests_only"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["GEMINI_API_KEY"] = ""
os.environ["DISABLE_RATE_LIMITING"] = "true"


@pytest.fixture()
def client():
    from database import engine
    from main import app
    from models import Base

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as test_client:
        yield test_client
