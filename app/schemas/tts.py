from pydantic import BaseModel

class TextInput(BaseModel):
    text: str
    voiceId: str

class TTSResponse(BaseModel):
    audioFile: str | None = None
    fallback_text: str | None = None
