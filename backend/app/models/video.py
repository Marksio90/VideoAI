"""
Model pojedynczego wideo (odcinka).
Ulepszenie: state machine z przejściami + pełne śledzenie pipeline.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class VideoStatus(StrEnum):
    PENDING = "pending"
    GENERATING_SCRIPT = "generating_script"
    GENERATING_HOOK = "generating_hook"
    GENERATING_VOICE = "generating_voice"
    FETCHING_MEDIA = "fetching_media"
    RENDERING = "rendering"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Video(BaseModel):
    __tablename__ = "videos"

    series_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("series.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    episode_number: Mapped[int] = mapped_column(Integer, default=1)

    # Treść
    title: Mapped[str] = mapped_column(String(500), default="")
    hook_text: Mapped[str] = mapped_column(Text, default="")
    script: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Status pipeline (state machine)
    status: Mapped[str] = mapped_column(
        String(50), default=VideoStatus.PENDING, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Pliki wygenerowane
    voice_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_duration_seconds: Mapped[float | None] = mapped_column(nullable=True)
    video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Media użyte w wideo (ulepszenie: śledzenie źródeł)
    media_assets: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=lambda: {"images": [], "clips": [], "music_track": None},
    )

    # Sceny (ulepszenie: granularna kontrola montażu)
    scenes: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        comment="Lista scen: [{text, start_time, end_time, media_url, subtitle}]",
    )

    # Harmonogram publikacji
    scheduled_publish_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Metryki (zbierane z API platform)
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=lambda: {
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "watch_time_seconds": 0,
            "avg_view_duration": 0,
            "retention_rate": 0,
        },
    )

    # IDs z platform zewnętrznych
    platform_ids: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=lambda: {"youtube_id": None, "tiktok_id": None, "instagram_id": None},
    )

    # Relacje
    series = relationship("Series", back_populates="videos")
    publish_jobs = relationship("PublishJob", back_populates="video", lazy="selectin")
