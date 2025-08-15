from fastapi import APIRouter, UploadFile, File
from ..schemas.tts import TextInput, TTSResponse
from ..services.tts_murf import murf_tts
from ..services.stt_aai import stt_transcribe
from ..constants import FALLBACK_AUDIO_URL, FALLBACK_TEXT
from ..logger import get_logger

router = APIRouter()
log = get_logger("lumeai.routes.tts")

@router.post("/text-to-speech", response_model=TTSResponse)
async def text_to_speech(req: TextInput):
    audio_url = murf_tts(req.text, req.voiceId)
    if audio_url:
        return TTSResponse(audioFile=audio_url)
    return TTSResponse(audioFile=FALLBACK_AUDIO_URL, fallback_text=FALLBACK_TEXT)

@router.post("/tts/echo", response_model=TTSResponse)
async def tts_echo(file: UploadFile = File(...)):
    audio_data = await file.read()
    transcript = stt_transcribe(audio_data)
    if not transcript:
        return TTSResponse(audioFile=FALLBACK_AUDIO_URL, fallback_text=FALLBACK_TEXT)

    audio_url = murf_tts(transcript, "en-US-natalie")
    if not audio_url:
        return TTSResponse(audioFile=FALLBACK_AUDIO_URL, fallback_text=FALLBACK_TEXT)

    return TTSResponse(audioFile=audio_url)
