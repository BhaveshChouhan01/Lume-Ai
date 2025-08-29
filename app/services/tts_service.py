import json
import asyncio
import websockets
import logging
from typing import Optional, Callable, Dict, Any

log = logging.getLogger("lumeai.tts_service")

class TTSService:
    """Service for handling Text-to-Speech"""
    
    def __init__(self):
        self.ws_url = "wss://api.murf.ai/v1/speech/stream-input"
        self.context_id = "lumeai-context-123"
    
    async def stream_tts(
        self, 
        text: str, 
        ws_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
        murf_key: str = None
    ):
        """Stream TTS audio generation"""
        if not murf_key:
            log.warning("No MURF API key provided, skipping TTS")
            if ws_callback:
                await ws_callback({
                    "type": "audio_error",
                    "message": "MURF API key not configured"
                })
            return
        
        uri = f"{self.ws_url}?api-key={murf_key}&sample_rate=44100&channel_type=MONO&format=WAV&context_id={self.context_id}"
        
        try:
            async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as ws:
                # Voice config
                voice_config = {
                    "voice_config": {
                        "voiceId": "en-US-Natalie", 
                        "style": "Conversational", 
                        "rate": 0, 
                        "pitch": 0, 
                        "variation": 1
                    }
                }
                await asyncio.wait_for(ws.send(json.dumps(voice_config)), timeout=5.0)
                
                audio_chunks = []
                
                # Send audio start signal
                if ws_callback:
                    await ws_callback({
                        "type": "audio_start", 
                        "context_id": self.context_id,
                        "message": "Starting audio generation..."
                    })
                
                # Send text for TTS
                try:
                    await asyncio.wait_for(ws.send(json.dumps({"text": text})), timeout=5.0)
                    
                    while True:
                        try:
                            response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                            data = json.loads(response)
                            
                            if "audio" in data and data["audio"]:
                                audio_b64 = data["audio"]
                                audio_chunks.append(audio_b64)
                                
                                if ws_callback:
                                    await ws_callback({
                                        "type": "audio_chunk", 
                                        "audio": audio_b64,
                                        "format": "wav_base64",
                                        "chunk_number": len(audio_chunks),
                                        "is_final": data.get("final", False)
                                    })
                            
                            if data.get("final"):
                                break
                                
                        except asyncio.TimeoutError:
                            break
                
                except asyncio.TimeoutError:
                    pass
                
                # Send end signal
                try:
                    await asyncio.wait_for(ws.send(json.dumps({"end": True})), timeout=5.0)
                    
                    if ws_callback:
                        await ws_callback({
                            "type": "audio_complete",
                            "total_chunks": len(audio_chunks),
                            "context_id": self.context_id,
                            "message": f"Audio generation complete with {len(audio_chunks)} chunks"
                        })
                        
                except Exception:
                    pass
                    
        except Exception as e:
            log.error(f"TTS Error: {e}")
            if ws_callback:
                await ws_callback({
                    "type": "audio_error",
                    "message": f"Audio generation failed: {str(e)}"
                })
