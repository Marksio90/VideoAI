"""
Konfiguracja aplikacji — centralne zarządzanie zmiennymi środowiskowymi.
Ulepszenie: walidacja Pydantic Settings + grupowanie po domenach + sensowne defaults.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Aplikacja ──
    APP_NAME: str = "AutoShorts"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── Baza danych ──
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql+asyncpg://autoshorts:autoshorts@localhost:5432/autoshorts"
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # ── Redis / Celery ──
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── JWT / Auth ──
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-USE-OPENSSL-RAND"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── OAuth2 Providers ──
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # ── OpenAI ──
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_MAX_TOKENS: int = 2000
    OPENAI_TEMPERATURE: float = 0.7

    # ── ElevenLabs TTS ──
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_DEFAULT_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel
    ELEVENLABS_MODEL_ID: str = "eleven_multilingual_v2"

    # ── Google Cloud TTS (fallback) ──
    GOOGLE_TTS_CREDENTIALS_PATH: str = ""

    # ── Storage (S3 / MinIO) ──
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET_NAME: str = "autoshorts-media"
    S3_REGION: str = "eu-central-1"

    # ── YouTube API ──
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""

    # ── TikTok API ──
    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""

    # ── Instagram / Meta ──
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""

    # ── Stripe ──
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_BASIC: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_AGENCY: str = ""

    # ── Sentry ──
    SENTRY_DSN: str = ""

    # ── Rate Limiting ──
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── FFmpeg ──
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"

    # ── Moderacja treści ──
    CONTENT_MODERATION_ENABLED: bool = True

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
