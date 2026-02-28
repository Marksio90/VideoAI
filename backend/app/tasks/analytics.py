"""
Zadania analityki — synchronizacja metryk z platform.
Ulepszenie: zbieranie z wielu platform + trend detection.
"""

import asyncio
import uuid
from datetime import datetime, timezone

import httpx
import structlog

from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.analytics.sync_all_metrics")
def sync_all_metrics():
    """Synchronizuje metryki ze wszystkich platform."""
    logger.info("Analytics: synchronizacja metryk")
    _run_async(_sync_metrics())


async def _sync_metrics():
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.models.platform_connection import PlatformConnection
    from app.models.series import Series
    from app.models.video import Video, VideoStatus

    async with async_session_factory() as db:
        # Pobierz opublikowane wideo
        result = await db.execute(
            select(Video).where(Video.status == VideoStatus.PUBLISHED)
        )
        published_videos = list(result.scalars().all())

        for video in published_videos:
            series_result = await db.execute(
                select(Series).where(Series.id == video.series_id)
            )
            series = series_result.scalar_one_or_none()
            if not series:
                continue

            # YouTube
            yt_id = (video.platform_ids or {}).get("youtube_id")
            if yt_id:
                conn_result = await db.execute(
                    select(PlatformConnection).where(
                        PlatformConnection.user_id == series.user_id,
                        PlatformConnection.platform == "youtube",
                        PlatformConnection.is_active.is_(True),
                    )
                )
                yt_conn = conn_result.scalar_one_or_none()
                if yt_conn:
                    try:
                        yt_stats = await _fetch_youtube_stats(yt_conn.access_token, yt_id)
                        video.metrics = {**video.metrics, **yt_stats}
                    except Exception as e:
                        logger.warning("YouTube stats błąd", error=str(e))

            db.add(video)

        await db.commit()
        logger.info("Analytics: zsynchronizowano", count=len(published_videos))


async def _fetch_youtube_stats(access_token: str, video_id: str) -> dict:
    """Pobiera statystyki wideo z YouTube Analytics."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "statistics",
                "id": video_id,
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        data = resp.json()

        items = data.get("items", [])
        if not items:
            return {}

        stats = items[0].get("statistics", {})
        return {
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
        }
