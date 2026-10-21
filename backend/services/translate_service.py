"""Translates DSA explanations into Hindi via the LLM gateway (cached)."""
from cache import cache_get, cache_set, make_key
from services import llm
from services.grading import safety
from services.grading.prompts import TRANSLATE_HINDI

TRANSLATION_TTL_SECONDS = 60 * 60 * 24 * 7


async def translate_to_hindi_with_gemini(text: str) -> dict:
    """Return {"translated_text", "translated"}; falls back to the English text."""
    key = make_key("translate_hi", TRANSLATE_HINDI.id, text)
    cached = cache_get("translate_hi", key)
    if cached:
        return {"translated_text": cached, "translated": True, "cached": True}

    prompt = "Text to translate:\n" + safety.wrap_untrusted("text", text, safety.new_boundary())
    try:
        translated = await llm.generate_text(
            "translate_hindi",
            system_instruction=TRANSLATE_HINDI.system_instruction,
            prompt=prompt,
            temperature=0.2,
        )
    except llm.LLMUnavailableError:
        return {"translated_text": text, "translated": False, "cached": False}

    cache_set("translate_hi", key, translated, TRANSLATION_TTL_SECONDS)
    return {"translated_text": translated, "translated": True, "cached": False}
