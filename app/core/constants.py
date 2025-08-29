from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT_DIR / "templates"
STATIC_DIR = ROOT_DIR / "static"
UPLOADS_DIR = ROOT_DIR / "uploads"

FALLBACK_TEXT = "I'm having trouble connecting right now."
FALLBACK_AUDIO_PATH = STATIC_DIR / "fallback.mp3"
FALLBACK_AUDIO_URL = "/static/fallback.mp3"
