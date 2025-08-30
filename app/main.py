import os
import time
import json
import logging
import threading
import queue
import asyncio
import websockets
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
load_dotenv()

# Import refactored services
from app.services.llm_service import LLMService
from app.services.tts_service import TTSService
from app.services.skills_service import SkillsService
from app.services.intent_service import IntentService
from app.core.config import get_config
from app.core.logger import get_logger
from app.core.constants import STATIC_DIR, TEMPLATES_DIR
from app.routes import agent, core, files

# Import AssemblyAI streaming
from assemblyai.streaming.v3 import (
    BeginEvent, StreamingClient, StreamingClientOptions, StreamingError,
    StreamingEvents, StreamingParameters, TerminationEvent, TurnEvent,
)

# Setup
config = get_config()
log = get_logger("lumeai")

app = FastAPI(title="LumeAI")
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# Mount static files and routes
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(core.router)
app.include_router(agent.router, prefix="/api")
app.include_router(files.router, prefix="/api")

# Global session storage
CHAT_HISTORY: dict[str, list[dict[str, str]]] = {}
SESSION_PERSONA: dict[str, str] = {}
SESSION_API_KEYS: dict[str, dict[str, str]] = {}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "assemblyai": bool(config.ASSEMBLYAI_API_KEY),
            "gemini": bool(config.GEMINI_API_KEY),
            "murf": bool(config.MURF_API_KEY)
        }
    }

# Queue-based audio streamer (kept as-is, working well)
class QueueAudioStreamer:
    def __init__(self, client: StreamingClient, max_queue_bytes: int = 10 * 1024 * 1024):
        self.client = client
        self.q: "queue.Queue[bytes | None]" = queue.Queue()
        self.stop_evt = threading.Event()
        self.thread: threading.Thread | None = None
        self._budget = max_queue_bytes
        self._inflight = 0

    def _gen(self):
        while not self.stop_evt.is_set():
            chunk = self.q.get()
            if chunk is None:
                break
            self._inflight -= len(chunk)
            yield chunk

    def start(self):
        def _run():
            try:
                self.client.stream(self._gen())
            except Exception as e:
                logging.exception("client.stream failed: %s", e)
        self.thread = threading.Thread(target=_run, daemon=True)
        self.thread.start()

    def send(self, chunk: bytes):
        sz = len(chunk)
        if self._inflight + sz > self._budget:
            return
        self._inflight += sz
        self.q.put(chunk)

    def stop(self):
        self.stop_evt.set()
        try:
            self.q.put(None)
        except Exception:
            pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

def get_api_key(user_keys: dict, key_name: str, fallback_env: str = None) -> str:
    """Get API key from user input or environment variables"""
    # Try user provided key first
    user_key = user_keys.get(key_name, "").strip()
    if user_key:
        return user_key
    
    # Fallback to environment variable
    if fallback_env:
        env_key = os.getenv(fallback_env, "").strip()
        if env_key:
            return env_key
    
    return ""

async def process_transcript_with_skills(session_id: str, text: str, ws_callback=None, api_keys=None):
    """Process user transcript using skills and LLM"""
    try:
        # Initialize services with proper API keys
        llm_service = LLMService()
        tts_service = TTSService()
        skills_service = SkillsService()
        intent_service = IntentService()
        
        # Update skills service with API keys from user or environment
        if api_keys:
            skills_service.weather_api_key = get_api_key(api_keys, 'weather_key', 'WEATHER_API_KEY')
            skills_service.news_api_key = get_api_key(api_keys, 'news_key', 'NEWS_API_KEY')
            skills_service.tmdb_api_key = get_api_key(api_keys, 'tmdb_key', 'TMDB_API_KEY')

        # Add user message to chat history
        history = CHAT_HISTORY.setdefault(session_id, [])
        history.append({"role": "user", "content": text})

        # Get persona for this session
        persona_prompt = SESSION_PERSONA.get(session_id, config.PERSONAS["default"])

        # Try skills first
        intent_data = intent_service.detect_intent(text)
        if intent_data and intent_data.get("intent"):
            log.info(f"Detected intent: {intent_data}")
            skill_response = await skills_service.execute_skill(intent_data)
            
            # Save skill response to history
            history.append({"role": "assistant", "content": skill_response})
            
            # Send complete text to client FIRST
            if ws_callback:
                await ws_callback({"type": "llm_response", "text": skill_response, "source": "skill"})
            
            # THEN send to TTS
            murf_key = get_api_key(api_keys, 'murf_key', 'MURF_API_KEY') if api_keys else ""
            if murf_key:
                await tts_service.stream_tts(skill_response, ws_callback, murf_key)
            
            return

        # Fallback to LLM if no skill matched
        log.info("No skill matched, using LLM...")
        
        # Build conversation with persona context
        conversation_prompt = f"System: {persona_prompt}\n\n"
        for turn in history:
            speaker = "Human" if turn["role"] == "user" else "Assistant"
            conversation_prompt += f"{speaker}: {turn['content']}\n"
        conversation_prompt += "\nAssistant: "

        # Get Gemini API key from user or fallback to environment
        gemini_key = get_api_key(api_keys, 'gemini_key', 'GEMINI_API_KEY') if api_keys else config.GEMINI_API_KEY
        if not gemini_key:
            raise ValueError("No Gemini API key available")

        # Stream LLM response
        collected_text = ""
        async for chunk in llm_service.stream_response(conversation_prompt, api_key=gemini_key):
            if chunk:
                collected_text += chunk
                # Send individual chunks for real-time display
                if ws_callback:
                    await ws_callback({"type": "llm_chunk", "text": chunk})

        # Send complete response
        if collected_text:
            history.append({"role": "assistant", "content": collected_text})
            if ws_callback:
                await ws_callback({"type": "llm_response", "text": collected_text, "source": "llm"})

        # Generate audio
        murf_key = get_api_key(api_keys, 'murf_key', 'MURF_API_KEY') if api_keys else ""
        if murf_key and collected_text:
            await tts_service.stream_tts(collected_text, ws_callback, murf_key)

    except Exception as e:
        log.exception(f"Processing error: {e}")
        error_message = f"Sorry, there was an issue: {str(e)}"
        if ws_callback:
            await ws_callback({"type": "error", "message": error_message})
        # Add error to history
        history = CHAT_HISTORY.setdefault(session_id, [])
        history.append({"role": "assistant", "content": error_message})

@app.websocket("/ws/stream")
async def ws_stream(websocket: WebSocket):
    await websocket.accept()
    session_id = websocket.query_params.get("session", f"anon-{int(time.time())}")
    persona_key = (websocket.query_params.get("persona") or "default").lower().strip()
    
    # Extract user API keys from query parameters
    user_api_keys = {
        'murf_key': websocket.query_params.get("murf_key", "").strip(),
        'assembly_key': websocket.query_params.get("assembly_key", "").strip(),
        'gemini_key': websocket.query_params.get("gemini_key", "").strip(),
        'weather_key': websocket.query_params.get("weather_key", "").strip(),
        'news_key': websocket.query_params.get("news_key", "").strip(),
        'tmdb_key': websocket.query_params.get("tmdb_key", "").strip(),
    }
    
    # Store API keys for this session
    SESSION_API_KEYS[session_id] = user_api_keys
    
    # Use user's AssemblyAI key or fallback to environment
    assembly_key = get_api_key(user_api_keys, 'assembly_key', 'ASSEMBLYAI_API_KEY')
    
    # Fallback unknown personas to default
    if persona_key not in config.PERSONAS:
        log.warning(f"Unknown persona '{persona_key}', using default")
        persona_key = "default"
    
    SESSION_PERSONA[session_id] = config.PERSONAS[persona_key]
    
    if not assembly_key:
        await websocket.send_text(json.dumps({
            "type": "error", 
            "message": "Missing AssemblyAI API key. Please configure it in settings or set ASSEMBLYAI_API_KEY environment variable."
        }))
        await websocket.close(code=4000, reason="Missing API key")
        return

    # Validate Gemini key as well since it's required for responses
    gemini_key = get_api_key(user_api_keys, 'gemini_key', 'GEMINI_API_KEY')
    if not gemini_key:
        await websocket.send_text(json.dumps({
            "type": "error", 
            "message": "Missing Gemini API key. Please configure it in settings or set GEMINI_API_KEY environment variable."
        }))
        await websocket.close(code=4001, reason="Missing Gemini key")
        return

    loop = asyncio.get_running_loop()
    
    async def ws_send(payload: dict):
        try:
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.send_text(json.dumps(payload))
        except Exception as e:
            log.warning(f"Failed to send WebSocket message: {e}")

    def sync_ws_send(payload: dict):
        asyncio.run_coroutine_threadsafe(ws_send(payload), loop)

    seen_texts = set()
    
    try:
        client = StreamingClient(StreamingClientOptions(api_key=assembly_key))
    except Exception as e:
        log.error(f"Failed to create AssemblyAI client: {e}")
        await ws_send({"type": "error", "message": "Invalid AssemblyAI API key"})
        await websocket.close(code=4002, reason="Invalid AssemblyAI key")
        return

    # AssemblyAI handlers
    def on_begin(client, event):
        sync_ws_send({"type": "info", "message": f"Connected with {persona_key} persona"})

    def on_turn(client, event):
        if not event.end_of_turn or not getattr(event, "turn_is_formatted", False):
            return
        
        text = event.transcript.strip()
        if not text or text in seen_texts:
            return
        seen_texts.add(text)

        log.info(f"Transcript: {text}")
        sync_ws_send({"type": "transcript", "text": text, "end_of_turn": True})

        if config.AUTO_ASSISTANT_REPLY:
            try:
                asyncio.run_coroutine_threadsafe(
                    process_transcript_with_skills(session_id, text, ws_send, user_api_keys), loop
                )
            except Exception as e:
                log.error(f"Error processing transcript: {e}")

    def on_termination(client, event):
        sync_ws_send({"type": "info", "message": "Session terminated"})

    def on_error(client, error):
        log.error(f"AssemblyAI error: {error}")
        sync_ws_send({"type": "error", "message": f"Speech recognition error: {str(error)}"})

    client.on(StreamingEvents.Begin, on_begin)
    client.on(StreamingEvents.Turn, on_turn)
    client.on(StreamingEvents.Termination, on_termination)
    client.on(StreamingEvents.Error, on_error)

    # Connect to AssemblyAI
    try:
        params = StreamingParameters(
            sample_rate=16000,
            format_turns=True,
            end_of_turn_confidence_threshold=0.75,
            min_end_of_turn_silence_when_confident=160,
            max_turn_silence=2400,
        )
        client.connect(params)
        log.info(f"Connected to AssemblyAI with persona: {persona_key}")
        await ws_send({"type": "info", "message": "Ready to process audio"})
    except Exception as e:
        log.error(f"AAI connection failed: {e}")
        await ws_send({"type": "error", "message": f"Speech recognition connection failed: {str(e)}"})
        await websocket.close(code=4003, reason="AssemblyAI connection failed")
        return

    # Audio forwarding setup
    send_fn = getattr(client, "send_audio", None) or getattr(client, "send_bytes", None)
    streamer: QueueAudioStreamer | None = None
    if not callable(send_fn):
        streamer = QueueAudioStreamer(client)
        streamer.start()

    # WebSocket message loop
    try:
        while True:
            msg = await websocket.receive()

            if "bytes" in msg and msg["bytes"]:
                try:
                    if streamer:
                        streamer.send(msg["bytes"])
                    else:
                        send_fn(msg["bytes"])
                except Exception as e:
                    log.warning(f"Audio send error: {e}")
                    break

            elif "text" in msg and msg["text"]:
                text = msg["text"]
                if text == "__stop":
                    log.info("Received stop signal")
                    try:
                        client.disconnect(terminate=True)
                    except Exception:
                        pass
                    break
                else:
                    await ws_send({"type": "echo", "text": text})

            elif msg.get("type") == "websocket.disconnect":
                break

    except WebSocketDisconnect:
        log.info(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        log.error(f"WebSocket error: {e}")
    finally:
        if streamer:
            streamer.stop()
        try:
            client.disconnect(terminate=True)
        except Exception:
            pass
        # Clean up session data
        if session_id in SESSION_API_KEYS:
            del SESSION_API_KEYS[session_id]
        log.info(f"Cleaned up session: {session_id}")

# Debug endpoints
@app.get("/debug/personas/{session_id}")
async def debug_persona(session_id: str):
    return {
        "session_id": session_id,
        "current_persona": SESSION_PERSONA.get(session_id, "None set"),
        "available_personas": list(config.PERSONAS.keys()),
        "chat_history_length": len(CHAT_HISTORY.get(session_id, [])),
        "has_api_keys": bool(SESSION_API_KEYS.get(session_id))
    }

@app.post("/reset/{session_id}")
async def reset_session(session_id: str):
    """Reset chat history and API keys for a session"""
    if session_id in CHAT_HISTORY:
        del CHAT_HISTORY[session_id]
    if session_id in SESSION_PERSONA:
        del SESSION_PERSONA[session_id]
    if session_id in SESSION_API_KEYS:
        del SESSION_API_KEYS[session_id]
    return {"message": f"Session {session_id} reset successfully"}

# Skill API endpoints
@app.get("/api/weather")
async def weather(city: str = Query(..., description="City name")):
    skills_service = SkillsService()
    return await skills_service.get_weather(city)

@app.get("/api/news")
async def news(query: str = Query(..., description="News search query")):
    skills_service = SkillsService()
    return await skills_service.get_news(query)

@app.get("/api/movies")
async def movies(query: str = Query(..., description="Movie search query")):
    skills_service = SkillsService()
    return await skills_service.search_movies(query)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)