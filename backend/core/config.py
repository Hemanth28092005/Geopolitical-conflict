from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

# Always point to the root .env regardless of where script is run from
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    database_url: str
    async_database_url: str
    redis_url: str
    app_env: str = "development"
    secret_key: str = "dev-secret"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    class Config:
        env_file = str(ROOT_DIR / ".env")
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
