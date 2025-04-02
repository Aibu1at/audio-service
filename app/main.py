from fastapi import FastAPI, UploadFile, HTTPException, Depends
from app.shemas import AudioFileCreate, AudioFileResponse, UserResponse, UserUpdate
from app.auth import get_current_user, create_access_token, refresh_access_token, YANDEX_CLIENT_ID, REDIRECT_URI, YANDEX_CLIENT_SECRET
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
async def callback_yandex(code: str, db: AsyncSession = Depends(get_db)):
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": YANDEX_CLIENT_ID,
        "client_secret": YANDEX_CLIENT_SECRET,
    }
    response = requests.post("https://oauth.yandex.ru/token", data=data)
    tokens = response.json()
    user_info = requests.get("https://login.yandex.ru/info", headers={"Authorization": f"Bearer {tokens['access_token']}"}).json()
    user_id = user_info["id"]
    
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        is_superuser = False
        result = await db.execute(select(User))
        if not result.scalars().first():
            is_superuser = True  #Первый пользаватель будет суперползователем
        user = User(id=user_id, email=user_info["default_email"], is_superuser=is_superuser)
        db.add(user)
        await db.commit()
    
    token = create_access_token({"sub": user_id})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/refresh")
async def refresh_token(user_id: str = Depends(get_current_user)):
    new_token = refresh_access_token(user_id)
    return {"access_token": new_token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserResponse)
async def get_user_me(user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).filter(User.id == user_id))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(id=user.id, email=user.email, is_superuser=user.is_superuser)

@app.put("/users/me", response_model=UserResponse)
async def update_user_me(user_id: str = Depends(get_current_user), user_data: UserUpdate = Depends(), db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).filter(User.id == user_id))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.email = user_data.email
    await db.commit()
    return UserResponse(id=user.id, email=user.email, is_superuser=user.is_superuser)

@app.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    superuser = (await db.execute(select(User).filter(User.id == current_user, User.is_superuser == True))).scalars().first()
    if not superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    #Файлы тоже удалим
    files = await db.execute(select(AudioFile).filter(AudioFile.user_id == user_id))
    for file in files.scalars().all():
        try:
            os.remove(file.path)
        except FileNotFoundError:
            pass
        await db.delete(file)
    await db.delete(user)
    await db.commit()
    return {"detail": "User deleted"}

@app.post("/audio/upload", response_model=AudioFileResponse)
async def upload_file(file: UploadFile, file_data: AudioFileCreate = Depends(), user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not file.filename.endswith(('.mp3', '.wav', '.ogg')): # По хорошему, нужна нормальная проверка типа файла а не это
        raise HTTPException(status_code=400, detail="Invalid file type")
    query = await db.execute(select(AudioFile).filter(AudioFile.user_id == user_id, AudioFile.name == file_data.name))
    existing_file = query.scalars().first()
    if existing_file:
        raise HTTPException(status_code=409, detail="Audio file with this name already exists")
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

