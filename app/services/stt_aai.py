from ..config import aai
from ..logger import get_logger

log = get_logger("lumeai.services.aai")

def stt_transcribe(audio_bytes: bytes) -> str | None:
    """Return transcript text or None on failure."""
    try:
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_bytes)
        text = getattr(transcript, "text", None)
        if not text:
            log.error("AssemblyAI returned empty transcript.")
            return None
        return text
    except Exception as e:
        log.exception("AssemblyAI STT error: %s", e)
        return None
