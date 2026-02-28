"""Model serii wideo — centralna jednostka organizacyjna."""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin


class Series(BaseModel, SoftDeleteMixin):
    __tablename__ = "series"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    # Konfiguracja generowania
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_template: Mapped[str] = mapped_column(
        Text,
        default=(
            "Napisz {duration}-sekundowy scenariusz filmiku z serii o {topic}. "
            "Zaczynaj intrygującym hookiem. Narracja w tonie {tone}. "
            "Uwzględnij 2-3 kluczowe punkty i wezwanie do subskrypcji na końcu."
        ),
    )
    language: Mapped[str] = mapped_column(String(10), default="pl")
    tone: Mapped[str] = mapped_column(String(50), default="edukacyjny")
    target_duration_seconds: Mapped[int] = mapped_column(default=60)

    # Harmonogram (ulepszenie: pełna konfiguracja cron-like)
    schedule_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=lambda: {
            "frequency": "3_per_week",
            "days": ["monday", "wednesday", "friday"],
            "time_utc": "14:00",
            "timezone": "Europe/Warsaw",
        },
    )
    is_active: Mapped[bool] = mapped_column(default=True)

    # Kanały publikacji
    publish_channels: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=lambda: {"youtube": False, "tiktok": False, "instagram": False},
    )

    # Styl wizualny (ulepszenie: konfiguracja wyglądu wideo)
    visual_style: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=lambda: {
            "font": "Montserrat-Bold",
            "font_size": 48,
            "font_color": "#FFFFFF",
            "subtitle_position": "bottom",
            "transition": "fade",
            "background_music": True,
            "branding_text": "",
        },
    )

    # Głos
    voice_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tts_provider: Mapped[str] = mapped_column(String(50), default="elevenlabs")

    # Statystyki
    total_episodes: Mapped[int] = mapped_column(default=0)

    # Relacje
    user = relationship("User", back_populates="series")
    videos = relationship("Video", back_populates="series", lazy="selectin")
