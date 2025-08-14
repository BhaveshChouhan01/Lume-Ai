from fastapi import FastAPI, HTTPException, Request, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv
import requests
import os
import google.generativeai as genai
import assemblyai as aai
import traceback

# Load environment variables
load_dotenv()

# API Keys
MURF_API_KEY = os.getenv("MURF_API_KEY")
MURF_API_URL = "https://api.murf.ai/v1/speech/generate"

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
if ASSEMBLYAI_API_KEY:
    aai.settings.api_key = ASSEMBLYAI_API_KEY
else:
    print("⚠ Missing AssemblyAI key")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("⚠ Missing Google Gemini API key")

# ---- In-memory datastore ----
chat_history = {}  # {session_id: [{"role": "user"/"assistant", "content": "text"}]}

# Fallbacks
FALLBACK_TEXT = "I'm having trouble connecting right now."
FALLBACK_AUDIO = "/static/fallback.mp3"  # Put an mp3 in /static

app = FastAPI()

# Static files & templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


class TextInput(BaseModel):
    text: str
    voiceId: str


class LLMQuery(BaseModel):
    prompt: str


# ---------- Helper Functions ----------
def murf_tts(text, voice_id):
    try:
        headers = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
        payload = {"text": text, "voiceId": voice_id}
        res = requests.post(MURF_API_URL, json=payload, headers=headers)
        res.raise_for_status()
        return res.json().get("audioFile")
    except Exception as e:
        print(f"❌ Murf TTS Error: {e}")
        return None


def stt_transcribe(audio_data):
    try:
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_data)
        return transcript.text
    except Exception as e:
        print(f"❌ AssemblyAI STT Error: {e}")
        return None


def llm_generate(prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"❌ Gemini LLM Error: {e}")
        return None


# ---------- Text-to-Speech ----------
@app.post("/text-to-speech")
async def text_to_speech(req: TextInput):
    audio_url = murf_tts(req.text, req.voiceId)
    if audio_url:
        return {"audioFile": audio_url}
    return {"audioFile": FALLBACK_AUDIO, "fallback_text": FALLBACK_TEXT}


# ---------- File Upload ----------
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as f:
        f.write(await file.read())
    return JSONResponse(content={
        "filename": file.filename,
        "content_type": file.content_type,
        "size": os.path.getsize(file_location)
    })


# ---------- TTS Echo ----------
@app.post("/tts/echo")
async def tts_echo(file: UploadFile = File(...)):
    audio_data = await file.read()
    transcript = stt_transcribe(audio_data)
    if not transcript:
        return {"audioFile": FALLBACK_AUDIO, "fallback_text": FALLBACK_TEXT}

    audio_url = murf_tts(transcript, "en-US-natalie")
    if not audio_url:
        return {"audioFile": FALLBACK_AUDIO, "fallback_text": FALLBACK_TEXT}

    return {"audioFile": audio_url, "transcript": transcript}


# ---------- LLM Query from Text ----------
@app.post("/llm/query-text")
async def llm_query_text(req: LLMQuery):
    response = llm_generate(req.prompt)
    if not response:
        return {"audioFile": FALLBACK_AUDIO, "fallback_text": FALLBACK_TEXT}
    return {"response": response}


# ---------- Echo Bot ----------
@app.post("/echo-bot")
async def echo_bot(file: UploadFile = File(...)):
    audio_data = await file.read()
    transcript = stt_transcribe(audio_data)
    if not transcript:
        return {"audioFile": FALLBACK_AUDIO, "fallback_text": FALLBACK_TEXT}

    llm_response = llm_generate(transcript)
    if not llm_response:
        return {"audioFile": FALLBACK_AUDIO, "fallback_text": FALLBACK_TEXT}

    audio_url = murf_tts(llm_response, "en-US-natalie")
    if not audio_url:
        return {"audioFile": FALLBACK_AUDIO, "fallback_text": FALLBACK_TEXT}

    return {"you_said": transcript, "llm_reply": llm_response, "audioFile": audio_url}


# ---------- Chat History Bot ----------
@app.post("/agent/chat/{session_id}")
async def agent_chat(session_id: str, file: UploadFile = File(...)):
    try:
        audio_data = await file.read()
        transcript = stt_transcribe(audio_data)
        if not transcript:
            raise ValueError("Transcription failed")

        history = chat_history.get(session_id, [])
        history.append({"role": "user", "content": transcript})

        prompt_text = ""
        for msg in history:
            if msg["role"] == "user":
                prompt_text += f"User: {msg['content']}\n"
            else:
                prompt_text += f"AI: {msg['content']}\n"

        llm_response = llm_generate(prompt_text)
        if not llm_response:
            raise ValueError("LLM failed")

        history.append({"role": "assistant", "content": llm_response})
        chat_history[session_id] = history

        audio_url = murf_tts(llm_response, "en-US-natalie")
        if not audio_url:
            raise ValueError("TTS failed")

        return {
            "you_said": transcript,
            "llm_reply": llm_response,
            "chat_history": history,
            "audioFile": audio_url
        }

    except Exception as e:
        print("❌ Error in /agent/chat:", traceback.format_exc())
        history = chat_history.get(session_id, [])
        history.append({"role": "assistant", "content": FALLBACK_TEXT})
        chat_history[session_id] = history
        return {
            "you_said": "",
            "llm_reply": FALLBACK_TEXT,
            "chat_history": history,
            "audioFile": FALLBACK_AUDIO,
            "fallback_text": FALLBACK_TEXT
        }
