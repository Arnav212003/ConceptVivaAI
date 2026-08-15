"""Translates DSA explanations into Hindi via Gemini."""
from config import GEMINI_API_KEY
from services.gemini_client import client


def translate_to_hindi_with_gemini(text):
    if not GEMINI_API_KEY or not client:
        return text  # no API available, just speak the English text as-is

    prompt = f"""
Translate the following DSA explanation into simple, clear Hindi (Devanagari script).
Keep technical/programming terms (array, function, loop, index, pointer, etc.) in English
since that's how Indian students normally read them — translate only the surrounding
explanation into Hindi.

Text to translate:
{text}

Return only the Hindi translation, nothing else.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception:
        return text  # fall back to English if translation fails
