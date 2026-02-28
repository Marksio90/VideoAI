"""
Zadanie publikacji — śledzenie statusu uploadu na każdą platformę.
Ulepszenie: osobne śledzenie per-platforma + retry tracking.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class PublishStatus(StrEnum):
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"


class PublishJob(BaseModel):
    __tablename__ = "publish_jobs"

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=PublishStatus.PENDING)
    platform_content_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    platform_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    metadata_extra: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    video = relationship("Video", back_populates="publish_jobs")
