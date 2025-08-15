from fastapi import APIRouter, UploadFile, File
from ..schemas.llm import LLMQuery, LLMTextResponse
from ..schemas.common import ChatMessage, ChatHistoryResponse
from ..services.stt_aai import stt_transcribe
from ..services.llm_gemini import llm_generate
from ..services.tts_murf import murf_tts
from ..constants import FALLBACK_AUDIO_URL, FALLBACK_TEXT
from ..logger import get_logger

router = APIRouter()
log = get_logger("lumeai.routes.agent")

# simple in-memory store (kept for parity with your original)
chat_history: dict[str, list[ChatMessage]] = {}

def build_prompt(history: list[ChatMessage]) -> str:
    prompt = []
    for msg in history:
        prefix = "User" if msg.role == "user" else "AI"
        prompt.append(f"{prefix}: {msg.content}")
    return "\n".join(prompt)

@router.post("/llm/query-text", response_model=LLMTextResponse)
async def llm_query_text(req: LLMQuery):
    response = llm_generate(req.prompt)
    if not response:
        return LLMTextResponse(audioFile=FALLBACK_AUDIO_URL, fallback_text=FALLBACK_TEXT)
    return LLMTextResponse(response=response)

@router.post("/echo-bot", response_model=LLMTextResponse)
async def echo_bot(file: UploadFile = File(...)):
    audio_data = await file.read()
    transcript = stt_transcribe(audio_data)
    if not transcript:
        return LLMTextResponse(audioFile=FALLBACK_AUDIO_URL, fallback_text=FALLBACK_TEXT)

    llm_response = llm_generate(transcript)
    if not llm_response:
        return LLMTextResponse(audioFile=FALLBACK_AUDIO_URL, fallback_text=FALLBACK_TEXT)

    audio_url = murf_tts(llm_response, "en-US-natalie")
    if not audio_url:
        return LLMTextResponse(audioFile=FALLBACK_AUDIO_URL, fallback_text=FALLBACK_TEXT)

    return LLMTextResponse(response=llm_response, audioFile=audio_url)

@router.post("/agent/chat/{session_id}", response_model=ChatHistoryResponse)
async def agent_chat(session_id: str, file: UploadFile = File(...)):
    try:
        audio_data = await file.read()
        transcript = stt_transcribe(audio_data)
        if not transcript:
            raise ValueError("Transcription failed")

        history = chat_history.get(session_id, [])
        history.append(ChatMessage(role="user", content=transcript))

        prompt_text = build_prompt(history)
        llm_response = llm_generate(prompt_text)
        if not llm_response:
            raise ValueError("LLM failed")

        history.append(ChatMessage(role="assistant", content=llm_response))
        chat_history[session_id] = history

        audio_url = murf_tts(llm_response, "en-US-natalie")
        if not audio_url:
            raise ValueError("TTS failed")

        return ChatHistoryResponse(
            you_said=transcript,
            llm_reply=llm_response,
            chat_history=history,
            audioFile=audio_url
        )

    except Exception as e:
        log.exception("Error in /agent/chat: %s", e)
        history = chat_history.get(session_id, [])
        history.append(ChatMessage(role="assistant", content=FALLBACK_TEXT))
        chat_history[session_id] = history
        return ChatHistoryResponse(
            you_said=None,
            llm_reply=FALLBACK_TEXT,
            chat_history=history,
            audioFile=FALLBACK_AUDIO_URL,
            fallback_text=FALLBACK_TEXT
        )
