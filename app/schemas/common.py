from pydantic import BaseModel
from typing import Any, List, Literal, Optional

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatHistoryResponse(BaseModel):
    you_said: str | None = None
    llm_reply: str | None = None
    chat_history: List[ChatMessage]
    audioFile: Optional[str] = None
    fallback_text: Optional[str] = None
