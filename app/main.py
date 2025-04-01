from fastapi import FastAPI, UploadFile, HTTPException, Depends, Form
from fastapi.responses import FileResponse
from app.shemas import AudioFileCreate, AudioFileResponse
from app.auth import get_current_user, create_access_token, YANDEX_CLIENT_ID, REDIRECT_URI, YANDEX_CLIENT_SECRET
import os
import aiofiles
import requests
from sqlalchemy.future import select
from app.models import User, AudioFile, engine, get_db, Base
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
@app.get("/login/yandex")
async def login_yandex():
    return {"url": f"https://oauth.yandex.ru/authorize?response_type=code&client_id={YANDEX_CLIENT_ID}&redirect_uri={REDIRECT_URI}"}

@app.get("/callback/yandex")
async def callback_yandex(code: str):
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": YANDEX_CLIENT_ID,
        "client_secret": YANDEX_CLIENT_SECRET,
    }
    response = requests.post("https://oauth.yandex.ru/token", data=data)
    tokens = response.json()
    user_info = requests.get("https://login.yandex.ru/info", headers={"Authorization": f"Bearer {tokens['access_token']}"}).json()
    token = create_access_token({"sub": user_info["id"]})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/users/me")
async def get_user(user_id: str = Depends(get_current_user)):
    return {"user_id": user_id}

@app.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: str = Depends(get_current_user)):
    pass

@app.post("/audio/upload", response_model=AudioFileResponse)
async def upload_file(file: UploadFile, file_data: AudioFileCreate = Depends(), user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not file.filename.endswith(('.mp3', '.wav', '.ogg')):
        raise HTTPException(status_code=400, detail="Invalid file type")
    file_path = os.path.join(UPLOAD_DIR, f"{user_id}_{file_data.name}")
    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)
    audio_file = AudioFile(name=file_data.name, path=file_path, user_id=user_id)
    db.add(audio_file)
    await db.commit()
    return AudioFileResponse(name=file_data.name, path=file_path)

@app.get("/audio/files", response_model=list[AudioFileResponse])
async def list_audio_files(user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AudioFile).where(AudioFile.user_id == user_id))
    files = result.scalars().all()
    return [AudioFileResponse(name=file.name, path=file.path) for file in files]

