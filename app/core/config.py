from pydantic_settings import BaseSettings
from pydantic import AnyUrl
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://edutrack:edutrack@localhost:5432/edutrack"
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    UPLOAD_DIR: str = "./uploads"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
