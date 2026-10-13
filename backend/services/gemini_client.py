"""Shared Gemini client used by the backend services."""
try:
    from google import genai
except Exception:
    genai = None

from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY) if (genai and GEMINI_API_KEY) else None
