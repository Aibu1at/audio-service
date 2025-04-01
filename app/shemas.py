from pydantic import BaseModel

class AudioFileCreate(BaseModel):
    name: str

class AudioFileResponse(BaseModel):
    name: str
    path: str