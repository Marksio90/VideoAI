"""
Endpointy analityki — statystyki wideo i serii.
Ulepszenie: agregowane metryki + trendy.
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.series import Series
from app.models.video import Video, VideoStatus
from app.models.user import User

router = APIRouter()


class DashboardStats(BaseModel):
    total_series: int
    total_videos: int
    published_videos: int
    total_views: int
    total_likes: int
    avg_retention_rate: float
    videos_this_month: int


class SeriesStats(BaseModel):
    series_id: uuid.UUID
    title: str
    total_episodes: int
    published: int
    total_views: int
    avg_views: float
    total_likes: int


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Agregowane statystyki panelu użytkownika."""
    # Zliczenie serii
    series_count = await db.execute(
        select(func.count()).select_from(
            select(Series)
            .where(Series.user_id == current_user.id, Series.deleted_at.is_(None))
            .subquery()
        )
    )

    # Pobranie wideo z metrykami
    videos_result = await db.execute(
        select(Video)
        .join(Series, Video.series_id == Series.id)
        .where(Series.user_id == current_user.id)
    )
    videos = list(videos_result.scalars().all())

    published = [v for v in videos if v.status == VideoStatus.PUBLISHED]
    total_views = sum(v.metrics.get("views", 0) for v in videos)
    total_likes = sum(v.metrics.get("likes", 0) for v in videos)

    retention_rates = [v.metrics.get("retention_rate", 0) for v in published if v.metrics.get("retention_rate")]
    avg_retention = sum(retention_rates) / len(retention_rates) if retention_rates else 0.0

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    videos_this_month = sum(1 for v in videos if v.created_at >= month_start)

    return DashboardStats(
        total_series=series_count.scalar() or 0,
        total_videos=len(videos),
        published_videos=len(published),
        total_views=total_views,
        total_likes=total_likes,
        avg_retention_rate=round(avg_retention, 2),
        videos_this_month=videos_this_month,
    )


@router.get("/series", response_model=list[SeriesStats])
async def get_series_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Statystyki per seria."""
    result = await db.execute(
        select(Series).where(
            Series.user_id == current_user.id,
            Series.deleted_at.is_(None),
        )
    )
    all_series = list(result.scalars().all())

    stats = []
    for s in all_series:
        videos_result = await db.execute(
            select(Video).where(Video.series_id == s.id)
        )
        videos = list(videos_result.scalars().all())
        published = [v for v in videos if v.status == VideoStatus.PUBLISHED]
        total_views = sum(v.metrics.get("views", 0) for v in videos)
        avg_views = total_views / len(published) if published else 0

        stats.append(
            SeriesStats(
                series_id=s.id,
                title=s.title,
                total_episodes=s.total_episodes,
                published=len(published),
                total_views=total_views,
                avg_views=round(avg_views, 1),
                total_likes=sum(v.metrics.get("likes", 0) for v in videos),
            )
        )

    return stats
