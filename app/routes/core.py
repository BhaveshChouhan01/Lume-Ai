from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from app.core.constants import TEMPLATES_DIR, STATIC_DIR, ROOT_DIR
import os

router = APIRouter()

# Only initialize templates if directory exists
if TEMPLATES_DIR.exists():
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
else:
    templates = None

@router.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    """Serve the main application page"""
    
    # Try to serve from templates directory first
    if templates:
        html_file = TEMPLATES_DIR / "index.html"
        if html_file.exists():
            return templates.TemplateResponse("index.html", {"request": request})
    
    # Fallback to serving from root directory
    root_html = ROOT_DIR / "index.html"
    if root_html.exists():
        return FileResponse(str(root_html))
    
    # Final fallback - basic HTML response
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>LumeAI - Real-time AI Voice Assistant</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; background: #1a1a1a; color: white; }
            .container { max-width: 600px; margin: 0 auto; text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🪞 LumeAI</h1>
            <p>Real-time AI Voice Assistant</p>
            <p>WebSocket streaming available at <code>/ws/stream</code></p>
            <p>Health check at <code>/health</code></p>
            <p>Please place your index.html file in the templates/ or root directory.</p>
        </div>
    </body>
    </html>
    """)