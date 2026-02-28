"""Schematy serii wideo."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ScheduleConfig(BaseModel):
    frequency: str = "3_per_week"
    days: list[str] = ["monday", "wednesday", "friday"]
    time_utc: str = "14:00"
    timezone: str = "Europe/Warsaw"


class VisualStyle(BaseModel):
    font: str = "Montserrat-Bold"
    font_size: int = 48
    font_color: str = "#FFFFFF"
    subtitle_position: str = "bottom"
    transition: str = "fade"
    background_music: bool = True
    branding_text: str = ""


class PublishChannels(BaseModel):
    youtube: bool = False
    tiktok: bool = False
    instagram: bool = False


class SeriesCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = ""
    topic: str = Field(min_length=1)
    prompt_template: str | None = None
    language: str = "pl"
    tone: str = "edukacyjny"
    target_duration_seconds: int = Field(default=60, ge=15, le=180)
    schedule_config: ScheduleConfig = ScheduleConfig()
    publish_channels: PublishChannels = PublishChannels()
    visual_style: VisualStyle = VisualStyle()
    voice_id: str | None = None
    tts_provider: str = "elevenlabs"


class SeriesUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    topic: str | None = None
    prompt_template: str | None = None
    language: str | None = None
    tone: str | None = None
    target_duration_seconds: int | None = None
    schedule_config: ScheduleConfig | None = None
    publish_channels: PublishChannels | None = None
    visual_style: VisualStyle | None = None
    voice_id: str | None = None
    tts_provider: str | None = None
    is_active: bool | None = None


class SeriesResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str
    topic: str
    prompt_template: str
    language: str
    tone: str
    target_duration_seconds: int
    schedule_config: dict[str, Any]
    publish_channels: dict[str, Any]
    visual_style: dict[str, Any]
    voice_id: str | None
    tts_provider: str
    is_active: bool
    total_episodes: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SeriesListResponse(BaseModel):
    items: list[SeriesResponse]
    total: int
    page: int
    page_size: int
