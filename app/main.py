from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .logger import get_logger
from .constants import STATIC_DIR, UPLOADS_DIR
from .routers import core, tts, files, agent

log = get_logger("lumeai.main")

app = FastAPI(title="LumeAI")

# Mount static + uploads
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
if not UPLOADS_DIR.exists():
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Routes
app.include_router(core.router)
app.include_router(tts.router)
app.include_router(files.router)
app.include_router(agent.router)

log.info("LumeAI app started.")
