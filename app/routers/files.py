import os
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from ..constants import UPLOADS_DIR
from ..logger import get_logger

router = APIRouter()
log = get_logger("lumeai.routes.files")

os.makedirs(UPLOADS_DIR, exist_ok=True)

@router.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    file_location = UPLOADS_DIR / file.filename
    with open(file_location, "wb") as f:
        f.write(await file.read())
    log.info("Saved upload: %s", file_location)
    return JSONResponse(content={
        "filename": file.filename,
        "content_type": file.content_type,
        "size": file_location.stat().st_size
    })
