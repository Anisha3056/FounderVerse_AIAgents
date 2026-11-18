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

    # SMTP configuration. Set these as environment variables on Render.
    email_smtp_host: str | None = None
    email_smtp_port: int = 587
    email_smtp_username: str | None = None
    email_smtp_password: str | None = None
    email_smtp_from: str | None = None
    email_smtp_use_tls: bool = True
    email_smtp_use_ssl: bool = False

    frontend_base_url: str = "https://founderverse-chi.vercel.app"
    email_verification_expiry_minutes: int = 30
    email_verification_resend_cooldown_seconds: int = 60

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
