from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    app_name: str = "FounderVerse API"
    app_version: str = "1.0.0"
    environment: str = "development"

    mongodb_uri: str
    mongodb_database: str = "founderverse"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"

    cors_origins: str = "http://localhost:5173,https://founderverse-chi.vercel.app"
    
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
