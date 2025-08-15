import os
from dotenv import load_dotenv
import assemblyai as aai
import google.generativeai as genai
from .logger import get_logger

log = get_logger("lumeai.config")

load_dotenv()

MURF_API_KEY = os.getenv("MURF_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not ASSEMBLYAI_API_KEY:
    log.warning("Missing AssemblyAI key")
else:
    aai.settings.api_key = ASSEMBLYAI_API_KEY

if not GEMINI_API_KEY:
    log.warning("Missing Google Gemini API key")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# Expose configured SDKs and keys if needed elsewhere
__all__ = ["MURF_API_KEY", "ASSEMBLYAI_API_KEY", "GEMINI_API_KEY", "aai", "genai"]
