from ..config import genai
from ..logger import get_logger

log = get_logger("lumeai.services.gemini")

def llm_generate(prompt: str) -> str | None:
    """Return model text or None on failure."""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", None)
        if not text:
            log.error("Gemini response had no text.")
            return None
        return text
    except Exception as e:
        log.exception("Gemini LLM error: %s", e)
        return None
