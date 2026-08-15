"""Centralized configuration and environment loading.

Kept separate from main.py so every layer (services, routes) can import
constants like GEMINI_API_KEY or ENABLE_CODE_EXECUTION without importing
the FastAPI app itself (which would risk circular imports).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# relative path "../.env.local" depended on the current working directory,
# so we use an absolute Path-based load like security.py
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env.local")
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
ENABLE_CODE_EXECUTION = os.getenv("ENABLE_CODE_EXECUTION", "false").lower() == "true"
