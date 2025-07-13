from pydantic import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"
    HF_TOKEN: str = ""
    ENV: str = "dev"
    # Add more as needed

    class Config:
        env_file = ".env"

@lru_cache
def get_settings():
    return Settings()
