# app/core/config.py
#
# Pydantic-settings reads values from your .env file automatically.
# Any variable defined here maps to a key in .env.
# This gives you type-safe, validated configuration across the app.

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # --- Database ---
    DATABASE_URL: str

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379"

    # --- JWT ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Email ---
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    class Config:
        env_file = ".env"


# lru_cache ensures we only read the .env file once,
# not on every request. This is a FastAPI best practice.
@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
