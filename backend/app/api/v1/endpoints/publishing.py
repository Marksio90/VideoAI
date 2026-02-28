"""Endpointy publikacji i zarządzania połączeniami z platformami."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.platform_connection import PlatformConnection
from app.models.publish_job import PublishJob
from app.models.user import User

router = APIRouter()


# ── Połączenia z platformami ──


class PlatformConnectionResponse:
    pass  # patrz niżej


from pydantic import BaseModel
from datetime import datetime


class PlatformConnectionOut(BaseModel):
    id: uuid.UUID
    platform: str
    platform_username: str | None
    channel_name: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ConnectPlatformRequest(BaseModel):
    platform: str  # youtube, tiktok, instagram
    auth_code: str
    redirect_uri: str


@router.get("/connections", response_model=list[PlatformConnectionOut])
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista podłączonych platform."""
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


@router.post("/connections", response_model=PlatformConnectionOut, status_code=status.HTTP_201_CREATED)
async def connect_platform(
    body: ConnectPlatformRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Podłączenie nowej platformy (wymiana auth_code na tokeny)."""
    from app.services.publishing.oauth_exchange import exchange_oauth_code

    token_data = await exchange_oauth_code(body.platform, body.auth_code, body.redirect_uri)

    # Sprawdź, czy istnieje już połączenie
    existing = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == body.platform,
        )
    )
    conn = existing.scalar_one_or_none()

    if conn:
        conn.access_token = token_data["access_token"]
        conn.refresh_token = token_data.get("refresh_token")
        conn.token_expires_at = token_data.get("expires_at")
        conn.platform_user_id = token_data.get("user_id")
        conn.platform_username = token_data.get("username")
        conn.channel_name = token_data.get("channel_name")
        conn.is_active = True
    else:
        conn = PlatformConnection(
            user_id=current_user.id,
            platform=body.platform,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_expires_at=token_data.get("expires_at"),
            platform_user_id=token_data.get("user_id"),
            platform_username=token_data.get("username"),
            channel_name=token_data.get("channel_name"),
        )

    db.add(conn)
    await db.flush()
    return conn


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_platform(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Odłączenie platformy."""
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.id == connection_id,
            PlatformConnection.user_id == current_user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Połączenie nie znalezione")

    conn.is_active = False
    db.add(conn)
    await db.flush()


# ── Historia publikacji ──


class PublishJobOut(BaseModel):
    id: uuid.UUID
    video_id: uuid.UUID
    platform: str
    status: str
    platform_url: str | None
    scheduled_at: datetime | None
    published_at: datetime | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/jobs", response_model=list[PublishJobOut])
async def list_publish_jobs(
    video_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista zadań publikacji."""
    from app.models.video import Video
    from app.models.series import Series

    query = (
        select(PublishJob)
        .join(Video, PublishJob.video_id == Video.id)
        .join(Series, Video.series_id == Series.id)
        .where(Series.user_id == current_user.id)
    )
    if video_id:
        query = query.where(PublishJob.video_id == video_id)

    result = await db.execute(query.order_by(PublishJob.created_at.desc()))
    return list(result.scalars().all())
