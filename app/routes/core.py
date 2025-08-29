from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.core.constants import TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@router.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    """Serve the main application page"""
    html_file = TEMPLATES_DIR / "index.html"
    if html_file.exists():
        return templates.TemplateResponse("index.html", {"request": request})
    return HTMLResponse("<h1>LumeAI - Real-time AI Voice Assistant</h1><p>WebSocket streaming at /ws/stream</p>")
