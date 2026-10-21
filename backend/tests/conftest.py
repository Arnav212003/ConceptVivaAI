import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


TEST_DB_PATH = Path(__file__).resolve().parent / "conceptviva_test.db"

os.environ["SESSION_SECRET_KEY"] = "test_secret_key_for_unit_tests_only"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["GEMINI_API_KEY"] = ""
os.environ["DISABLE_RATE_LIMITING"] = "true"
# Tests build the schema with create_all; Alembic is exercised in test_migrations.py.
os.environ["AUTO_MIGRATE_SQLITE"] = "false"
os.environ["REDIS_URL"] = ""
os.environ["LLM_BACKOFF_BASE_SECONDS"] = "0"
os.environ["APP_ENV"] = "test"


class FakeLLMBackend:
    """Returns canned JSON per output schema; records every call for assertions."""

    model_name = "fake-model"

    def __init__(self, responses=None):
        self.responses = dict(responses or {})
        self.calls = []

    async def generate(self, *, system_instruction, prompt, response_schema, temperature):
        self.calls.append({
            "system_instruction": system_instruction,
            "prompt": prompt,
            "schema": response_schema.__name__ if response_schema else None,
        })
        key = response_schema.__name__ if response_schema else "text"
        response = self.responses[key]
        if isinstance(response, Exception):
            raise response
        if callable(response):
            response = response(prompt)
        return response if isinstance(response, str) else json.dumps(response)


@pytest.fixture()
def fake_llm():
    from services import llm

    backend = FakeLLMBackend()
    llm.set_llm_backend(backend)
    yield backend
    llm.set_llm_backend(None)


@pytest.fixture(autouse=True)
def _reset_llm_and_cache():
    from cache import clear_memory_cache
    from redis_client import set_redis
    from services import llm

    llm.set_llm_backend(None)
    set_redis(None)
    clear_memory_cache()
    yield
    llm.set_llm_backend(None)
    set_redis(None)


@pytest.fixture()
def client():
    from database import engine
    from main import app
    from models import Base

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as test_client:
        yield test_client
