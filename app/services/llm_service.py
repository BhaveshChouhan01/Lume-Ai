import os
import asyncio
import logging
from typing import AsyncGenerator, Optional

try:
    from google import genai
except ImportError:
    genai = None

log = logging.getLogger("lumeai.llm_service")

class LLMService:
    """Service for handling LLM interactions"""
    
    def __init__(self):
        self.client = None
    
    def _make_client(self, api_key: str = None):
        """Create GenAI client with API key"""
        if genai is None:
            raise RuntimeError("google-genai library not available. Install with: pip install google-genai")
        
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("No Gemini API key provided")
        
        return genai.Client(api_key=key)
    
    def _extract_text_from_chunk(self, chunk) -> str:
        """Extract text from streaming chunk"""
        if chunk is None:
            return ""
        
        # Try direct text attribute
        text = getattr(chunk, "text", None)
        if text:
            return text
        
        # Try candidates structure
        try:
            candidates = getattr(chunk, "candidates", None)
            if candidates:
                first = candidates[0]
                content = getattr(first, "content", None)
                if content:
                    parts = getattr(content, "parts", None)
                    if parts and len(parts) > 0:
                        return getattr(parts[0], "text", "")
        except Exception:
            pass
        
        # Try dictionary structure
        try:
            if isinstance(chunk, dict):
                if "text" in chunk:
                    return chunk["text"]
                candidates = chunk.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
        except Exception:
            pass
        
        return str(chunk) if chunk else ""
    
    async def stream_response(
        self, 
        prompt: str, 
        model: str = "gemini-2.5-flash",
        api_key: str = None,
        system_instruction: str = None,
        generation_config: dict = None
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response"""
        client = self._make_client(api_key)
        contents = [prompt]
        call_kwargs = {}
        
        if system_instruction:
            call_kwargs["system_instruction"] = system_instruction
        if generation_config:
            call_kwargs["generation_config"] = generation_config
        
        try:
            stream_iter = client.models.generate_content_stream(
                model=model, 
                contents=contents, 
                **call_kwargs
            )
            
            for chunk in stream_iter:
                text = self._extract_text_from_chunk(chunk)
                if text:
                    yield text
                    
        except Exception as e:
            log.exception(f"LLM streaming error: {e}")
            raise
    
    async def generate_response(
        self, 
        prompt: str, 
        model: str = "gemini-2.5-flash",
        api_key: str = None
    ) -> Optional[str]:
        """Generate single response (non-streaming)"""
        try:
            client = self._make_client(api_key)
            response = client.models.generate_content(model=model, contents=[prompt])
            
            # Extract text from response
            if hasattr(response, 'text') and response.text:
                return response.text
            elif hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        part = candidate.content.parts[0]
                        if hasattr(part, 'text'):
                            return part.text
            
            return None
            
        except Exception as e:
            log.exception(f"LLM generate error: {e}")
            return None
