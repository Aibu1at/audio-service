import os
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
import jwt
from jwt.exceptions import InvalidTokenError
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

YANDEX_CLIENT_ID = os.getenv("YANDEX_CLIENT_ID")
YANDEX_CLIENT_SECRET = os.getenv("YANDEX_CLIENT_SECRET")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
REDIRECT_URI = "http://localhost:8000/callback/yandex"

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"https://oauth.yandex.ru/authorize",
    tokenUrl="https://oauth.yandex.ru/token"
)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        return user_id
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def refresh_access_token(user_id: str):
    try:
        new_token = create_access_token({"sub": user_id})
        return new_token
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")