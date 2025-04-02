from pydantic import BaseModel

class AudioFileCreate(BaseModel):
    name: str

class AudioFileResponse(BaseModel):
    name: str
    path: str

class UserResponse(BaseModel):
    id: str
    email: str
    is_superuser: bool

class UserUpdate(BaseModel):
    email: str