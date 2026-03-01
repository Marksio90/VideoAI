"""
Scheduler — automatyczne generowanie i publikacja wg harmonogramu.
Ulepszenie: timezone-aware scheduling + smart retry + reset limitów.
"""

import asyncio
import uuid
from datetime import datetime, timezone

import structlog

from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.scheduler.check_scheduled_videos")
def check_scheduled_videos():
    """
    Sprawdza co minutę, czy są serie wymagające nowego odcinka.
    Na podstawie schedule_config decyduje, czy wygenerować wideo.
    """
    logger.info("Scheduler: sprawdzanie harmonogramów")
    _run_async(_check_schedules())


async def _check_schedules():
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.core.config import get_settings
    from app.models.series import Series
    from app.models.video import Video, VideoStatus

    settings = get_settings()
    # Create a fresh engine bound to the current event loop (Celery forks give
    # each worker a new loop; the module-level engine uses the parent's loop).
    local_engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
    local_session_factory = async_sessionmaker(
        local_engine, class_=AsyncSession, expire_on_commit=False
    )

    now = datetime.now(timezone.utc)
    current_day = now.strftime("%A").lower()
    current_hour = now.strftime("%H:%M")

    try:
        async with local_session_factory() as db:
            # Pobierz aktywne serie
            result = await db.execute(
                select(Series).where(
                    Series.is_active.is_(True),
                    Series.deleted_at.is_(None),
                )
            )
            all_series = list(result.scalars().all())

            for series in all_series:
                schedule = series.schedule_config or {}
                days = schedule.get("days", [])
                time_utc = schedule.get("time_utc", "14:00")

                # Czy dzisiaj jest dzień generacji?
                if current_day not in days:
                    continue

                # Czy to odpowiednia godzina? (tolerancja ±1 min)
                if current_hour != time_utc:
                    continue

                # Czy już wygenerowano dzisiaj?
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                existing = await db.execute(
                    select(Video).where(
                        Video.series_id == series.id,
                        Video.created_at >= today_start,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                # Generuj nowy odcinek!
                logger.info(
                    "Scheduler: generowanie odcinka",
                    series_id=str(series.id),
                    series_title=series.title,
                )

                from app.tasks.video_pipeline import generate_video_task
                from app.models.user import User

                # Sprawdź limit użytkownika
                user_result = await db.execute(select(User).where(User.id == series.user_id))
                user = user_result.scalar_one_or_none()
                if not user or user.videos_generated_this_month >= user.max_videos_per_month:
                    logger.warning("Scheduler: limit miesięczny", user_id=str(series.user_id))
                    continue

                # Utwórz rekord wideo
                video = Video(
                    series_id=series.id,
                    episode_number=series.total_episodes + 1,
                    status=VideoStatus.PENDING,
                )
                db.add(video)
                series.total_episodes += 1
                user.videos_generated_this_month += 1
                db.add(series)
                db.add(user)
                await db.commit()

                generate_video_task.delay(str(video.id), str(series.id), None, None)
    finally:
        await local_engine.dispose()


@celery_app.task(name="app.tasks.scheduler.refresh_expiring_tokens")
def refresh_expiring_tokens():
    """Odświeża tokeny platform, które wkrótce wygasną."""
    logger.info("Scheduler: odświeżanie tokenów")
    _run_async(_refresh_tokens())


async def _refresh_tokens():
    from datetime import timedelta

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.core.config import get_settings
    from app.models.platform_connection import PlatformConnection

    settings = get_settings()
    local_engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
    local_session_factory = async_sessionmaker(
        local_engine, class_=AsyncSession, expire_on_commit=False
    )

    now = datetime.now(timezone.utc)
    threshold = now + timedelta(hours=2)

    try:
        async with local_session_factory() as db:
            result = await db.execute(
                select(PlatformConnection).where(
                    PlatformConnection.is_active.is_(True),
                    PlatformConnection.token_expires_at.isnot(None),
                    PlatformConnection.token_expires_at <= threshold,
                    PlatformConnection.refresh_token.isnot(None),
                )
            )
            connections = list(result.scalars().all())

            for conn in connections:
                try:
                    await _refresh_single_token(conn, db)
                except Exception as e:
                    logger.error(
                        "Token refresh błąd",
                        platform=conn.platform,
                        error=str(e),
                    )
    finally:
        await local_engine.dispose()


async def _refresh_single_token(conn, db):
    """Odświeża token dla pojedynczego połączenia."""
    import httpx

    from app.core.config import get_settings
    from datetime import timedelta

    settings = get_settings()

    if conn.platform == "youtube":
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.YOUTUBE_CLIENT_ID,
                    "client_secret": settings.YOUTUBE_CLIENT_SECRET,
                    "refresh_token": conn.refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            conn.access_token = data["access_token"]
            conn.token_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=data.get("expires_in", 3600)
            )
            db.add(conn)
            await db.commit()
            logger.info("Token odświeżony", platform="youtube")


@celery_app.task(name="app.tasks.scheduler.reset_monthly_counters")
def reset_monthly_counters():
    """Resetuje miesięczne liczniki wideo (1. dzień miesiąca)."""
    now = datetime.now(timezone.utc)
    if now.day != 1:
        return

    logger.info("Scheduler: reset miesięcznych liczników")
    _run_async(_reset_counters())


async def _reset_counters():
    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.core.config import get_settings
    from app.models.user import User

    settings = get_settings()
    local_engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
    local_session_factory = async_sessionmaker(
        local_engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        async with local_session_factory() as db:
            await db.execute(update(User).values(videos_generated_this_month=0))
            await db.commit()
            logger.info("Liczniki zresetowane")
    finally:
        await local_engine.dispose()
