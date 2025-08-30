import os
import asyncio
import logging
from typing import AsyncGenerator, Optional

try:
    import google.generativeai as genai
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
            raise RuntimeError("google-generativeai library not available. Install with: pip install google-generativeai")
        
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("No Gemini API key provided")
        
        # Configure the API key
        genai.configure(api_key=key)
        return genai
    
    def _extract_text_from_response(self, response) -> str:
        """Extract text from Gemini response"""
        if response is None:
            return ""
        
        try:
            # For google-generativeai, the response has a text attribute
            if hasattr(response, 'text') and response.text:
                return response.text
            
            # Fallback: try candidates structure
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        part = candidate.content.parts[0]
                        if hasattr(part, 'text'):
                            return part.text
        except Exception as e:
            log.warning(f"Error extracting text from response: {e}")
        
        return ""
    
    def _extract_text_from_chunk(self, chunk) -> str:
        """Extract text from streaming chunk"""
        if chunk is None:
            return ""
        
        try:
            # For google-generativeai streaming, chunks have a text attribute
            if hasattr(chunk, 'text') and chunk.text:
                return chunk.text
            
            # Fallback: try candidates structure
            if hasattr(chunk, 'candidates') and chunk.candidates:
                candidate = chunk.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        part = candidate.content.parts[0]
                        if hasattr(part, 'text'):
                            return part.text
        except Exception as e:
            log.warning(f"Error extracting text from chunk: {e}")
        
        return ""
    
    async def stream_response(
        self, 
        prompt: str, 
        model: str = "gemini-1.5-flash",
        api_key: str = None,
        system_instruction: str = None,
        generation_config: dict = None
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response"""
        client = self._make_client(api_key)
        
        try:
            # Create the model
            model_instance = client.GenerativeModel(
                model_name=model,
                system_instruction=system_instruction
            )
            
            # Set up generation config
            config = generation_config or {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
            
            # Generate content stream
            response = model_instance.generate_content(
                prompt,
                generation_config=config,
                stream=True
            )
            
            for chunk in response:
                text = self._extract_text_from_chunk(chunk)
                if text:
                    yield text
                    
        except Exception as e:
            log.exception(f"LLM streaming error: {e}")
            raise
    
    async def generate_response(
        self, 
        prompt: str, 
        model: str = "gemini-1.5-flash",
        api_key: str = None,
        system_instruction: str = None
    ) -> Optional[str]:
        """Generate single response (non-streaming)"""
        try:
            client = self._make_client(api_key)
            
            # Create the model
            model_instance = client.GenerativeModel(
                model_name=model,
                system_instruction=system_instruction
            )
            
            # Generate content
            response = model_instance.generate_content(prompt)
            return self._extract_text_from_response(response)
            
        except Exception as e:
            log.exception(f"LLM generate error: {e}")
            return None