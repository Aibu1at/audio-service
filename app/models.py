from sqlalchemy import Column, String, Integer, ForeignKey, Boolean
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    email = Column(String, nullable=True)
    is_superuser = Column(Boolean, default=False)

class AudioFile(Base):
    __tablename__ = "audio_files"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    path = Column(String)
    user_id = Column(String, ForeignKey("users.id"))

DATABASE_URL = "postgresql+asyncpg://user:password@db:5432/audio_db"
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session