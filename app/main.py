from fastapi import FastAPI, UploadFile, HTTPException, Depends, Form
from fastapi.responses import FileResponse
from app.shemas import AudioFileCreate, AudioFileResponse
import os
import aiofiles

app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/audio/upload", response_model=AudioFileResponse)
async def upload_file(file: UploadFile, file_data: AudioFileCreate = Depends()):
    file_path = os.path.join(UPLOAD_DIR, file_data.name)
    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)
    return AudioFileResponse(name=file_data.name, path=file_path)

@app.get("/audio/files", response_model=list[AudioFileResponse])
async def list_audio_files():
    files = [{"name": f, "path": os.path.join(UPLOAD_DIR, f)} for f in os.listdir(UPLOAD_DIR)]
    return files

