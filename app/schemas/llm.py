from pydantic import BaseModel

class LLMQuery(BaseModel):
    prompt: str

class LLMTextResponse(BaseModel):
    response: str | None = None
    audioFile: str | None = None
    fallback_text: str | None = None
