from fastapi import APIRouter, UploadFile, File, Body, Query
from typing import List
from app.schemas.llm import LLMQuery, LLMTextResponse
from app.schemas.common import ChatMessage, ChatHistoryResponse
from app.core.constants import FALLBACK_AUDIO_URL, FALLBACK_TEXT
from app.core.logger import get_logger
from app.services.llm_service import LLMService
from app.services.tts_service import TTSService
from app.services.skills_service import SkillsService
from app.services.intent_service import IntentService

router = APIRouter()
log = get_logger("lumeai.routes.agent")

# Initialize services
llm_service = LLMService()
tts_service = TTSService()
skills_service = SkillsService()
intent_service = IntentService()

# Simple in-memory store for legacy compatibility
chat_history: dict[str, list[ChatMessage]] = {}

def build_prompt(history: List[ChatMessage]) -> str:
    """Build conversation prompt from history"""
    prompt = []
    for msg in history[-12:]:  # Keep last 12 turns
        prefix = "User" if msg.role == "user" else "AI"
        prompt.append(f"{prefix}: {msg.content}")
    return "\n".join(prompt)

@router.post("/llm/query-text", response_model=LLMTextResponse)
async def llm_query_text(req: LLMQuery):
    """Generate LLM response from text prompt"""
    response = await llm_service.generate_response(req.prompt)
    if not response:
        return LLMTextResponse(audioFile=FALLBACK_AUDIO_URL, fallback_text=FALLBACK_TEXT)
    return LLMTextResponse(response=response)

@router.post("/chat-smart", response_model=ChatHistoryResponse)
async def chat_smart(req: LLMQuery = Body(...), session_id: str = Query("default")):
    """Smart chat with skill routing"""
    user_text = (req.prompt or "").strip()
    if not user_text:
        return ChatHistoryResponse(
            you_said="",
            llm_reply=FALLBACK_TEXT,
            chat_history=[],
            audioFile=FALLBACK_AUDIO_URL,
            fallback_text=FALLBACK_TEXT
        )

    # Update history
    history = chat_history.get(session_id, [])
    history.append(ChatMessage(role="user", content=user_text))

    # Try skills first
    reply_text = None
    intent_data = intent_service.detect_intent(user_text)
    if intent_data and intent_data.get("intent"):
        try:
            reply_text = await skills_service.execute_skill(intent_data)
        except Exception as e:
            log.exception("Skill execution error: %s", e)
            reply_text = None

    # Fallback to LLM
    if not reply_text:
        prompt_text = build_prompt(history)
        reply_text = await llm_service.generate_response(prompt_text) or FALLBACK_TEXT

    history.append(ChatMessage(role="assistant", content=reply_text))
    chat_history[session_id] = history

    return ChatHistoryResponse(
        you_said=user_text,
        llm_reply=reply_text,
        chat_history=history,
        audioFile=None,  # No TTS in this endpoint
        fallback_text=None
    )
