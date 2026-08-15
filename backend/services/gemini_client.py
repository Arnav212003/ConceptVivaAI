"""Single shared Gemini client instance.

Every service module imports `client` from here instead of constructing its
own, so there is exactly one client for the whole backend (load-once pattern).
"""
try:
    from google import genai
except Exception:
    genai = None

from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY) if (genai and GEMINI_API_KEY) else None
