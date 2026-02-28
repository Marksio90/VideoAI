"""Schematy wideo."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class VideoCreateRequest(BaseModel):
    """Ręczne tworzenie wideo (bez automatycznej generacji)."""
    series_id: uuid.UUID
    title: str = ""
    script: str | None = None


class VideoUpdateRequest(BaseModel):
    title: str | None = None
    script: str | None = None
    hook_text: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    scheduled_publish_at: datetime | None = None


class VideoGenerateRequest(BaseModel):
    """Żądanie automatycznej generacji wideo."""
    series_id: uuid.UUID
    custom_topic: str | None = None
    custom_prompt: str | None = None


class VideoApproveRequest(BaseModel):
    """Zatwierdzenie wideo do publikacji."""
    publish_channels: list[str] = Field(default_factory=list)
    scheduled_publish_at: datetime | None = None


class SceneResponse(BaseModel):
    text: str
    start_time: float
    end_time: float
    media_url: str | None = None
    subtitle: str = ""


class VideoResponse(BaseModel):
    id: uuid.UUID
    series_id: uuid.UUID
    episode_number: int
    title: str
    hook_text: str
    script: str
    description: str
    tags: list[str]
    status: str
    error_message: str | None
    voice_url: str | None
    voice_duration_seconds: float | None
    video_url: str | None
    thumbnail_url: str | None
    scenes: list[dict[str, Any]]
    media_assets: dict[str, Any]
    scheduled_publish_at: datetime | None
    published_at: datetime | None
    metrics: dict[str, Any]
    platform_ids: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    items: list[VideoResponse]
    total: int
    page: int
    page_size: int
