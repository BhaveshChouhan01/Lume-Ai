import requests
from ..config import MURF_API_KEY
from ..logger import get_logger

log = get_logger("lumeai.services.murf")

MURF_API_URL = "https://api.murf.ai/v1/speech/generate"

def murf_tts(text: str, voice_id: str) -> str | None:
    """Return hosted audio URL for TTS or None on failure."""
    if not MURF_API_KEY:
        log.error("Murf API key missing.")
        return None
    try:
        headers = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
        payload = {"text": text, "voiceId": voice_id}
        res = requests.post(MURF_API_URL, json=payload, headers=headers, timeout=30)
        res.raise_for_status()
        audio_url = res.json().get("audioFile")
        if not audio_url:
            log.error("Murf response missing 'audioFile'.")
            return None
        return audio_url
    except Exception as e:
        log.exception("Murf TTS error: %s", e)
        return None
