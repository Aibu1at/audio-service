import os
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
import jwt
from jwt.exceptions import InvalidTokenError
import requests
from dotenv import load_dotenv

load_dotenv()

YANDEX_CLIENT_ID = os.getenv("YANDEX_CLIENT_ID")
YANDEX_CLIENT_SECRET = os.getenv("YANDEX_CLIENT_SECRET")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
REDIRECT_URI = "http://localhost:8000/callback/yandex"

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"https://oauth.yandex.ru/authorize?response_type=code&client_id={YANDEX_CLIENT_ID}",
    tokenUrl="https://oauth.yandex.ru/token",
)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)