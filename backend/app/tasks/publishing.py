"""
Zadania publikacji wideo na platformach.
Ulepszenie: osobne zadania per platforma + retry + status tracking.
"""

import asyncio
import uuid
from datetime import datetime, timezone

import structlog
from celery import shared_task

from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.publishing.schedule_publish_task")
def schedule_publish_task(video_id: str, channels: list[str]):
    """Tworzy zadania publikacji dla wybranych kanałów."""
    logger.info("Planowanie publikacji", video_id=video_id, channels=channels)
    _run_async(_create_publish_jobs(video_id, channels))


async def _create_publish_jobs(video_id: str, channels: list[str]):
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.models.publish_job import PublishJob, PublishStatus
    from app.models.video import Video

    async with async_session_factory() as db:
        result = await db.execute(select(Video).where(Video.id == uuid.UUID(video_id)))
        video = result.scalar_one_or_none()
        if not video:
            return

        for channel in channels:
            job = PublishJob(
                video_id=video.id,
                platform=channel,
                status=PublishStatus.PENDING,
                scheduled_at=video.scheduled_publish_at,
            )
            db.add(job)

        await db.commit()

        # Natychmiastowa publikacja jeśli nie zaplanowano na przyszłość
        for channel in channels:
            if not video.scheduled_publish_at or video.scheduled_publish_at <= datetime.now(timezone.utc):
                publish_to_platform_task.delay(video_id, channel)


@celery_app.task(
    name="app.tasks.publishing.publish_to_platform_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def publish_to_platform_task(self, video_id: str, platform: str):
    """Publikuje wideo na konkretną platformę."""
    logger.info("Publikacja start", video_id=video_id, platform=platform)
    try:
        _run_async(_publish(video_id, platform))
    except Exception as exc:
        logger.error("Publikacja błąd", video_id=video_id, platform=platform, error=str(exc))
        _run_async(_update_publish_job(video_id, platform, "failed", str(exc)))
        raise self.retry(exc=exc)


async def _publish(video_id: str, platform: str):
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.models.platform_connection import PlatformConnection
    from app.models.publish_job import PublishJob, PublishStatus
    from app.models.series import Series
    from app.models.video import Video, VideoStatus
    from app.services.video.storage import StorageService

    async with async_session_factory() as db:
        result = await db.execute(select(Video).where(Video.id == uuid.UUID(video_id)))
        video = result.scalar_one()

        series_result = await db.execute(select(Series).where(Series.id == video.series_id))
        series = series_result.scalar_one()

        # Pobierz połączenie z platformą
        conn_result = await db.execute(
            select(PlatformConnection).where(
                PlatformConnection.user_id == series.user_id,
                PlatformConnection.platform == platform,
                PlatformConnection.is_active.is_(True),
            )
        )
        connection = conn_result.scalar_one_or_none()
        if not connection:
            raise RuntimeError(f"Brak aktywnego połączenia z {platform}")

        # Pobierz plik wideo do tymczasowego katalogu
        import tempfile

        storage = StorageService()
        video_key = video.video_url.split("/")[-1] if video.video_url else None
        if not video_key:
            raise RuntimeError("Brak pliku wideo do publikacji")

        # Dla uproszczenia: generujemy presigned URL
        presigned_url = storage.get_presigned_url(
            f"videos/{series.id}/{video_key}", expires_in=3600
        )

        # Update job status
        job_result = await db.execute(
            select(PublishJob).where(
                PublishJob.video_id == video.id,
                PublishJob.platform == platform,
                PublishJob.status == PublishStatus.PENDING,
            )
        )
        job = job_result.scalar_one_or_none()
        if job:
            job.status = PublishStatus.UPLOADING
            db.add(job)
            await db.commit()

        # Publikuj
        publish_result = {}
        if platform == "youtube":
            from app.services.publishing.youtube_publisher import YouTubePublisher

            publisher = YouTubePublisher()
            # Potrzebujemy lokalny plik — pobierz z S3
            import httpx

            tmp_path = tempfile.mktemp(suffix=".mp4")
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.get(presigned_url)
                with open(tmp_path, "wb") as f:
                    f.write(resp.content)

            publish_result = await publisher.upload(
                access_token=connection.access_token,
                video_path=tmp_path,
                title=video.title,
                description=video.description,
                tags=video.tags or [],
            )
            video.platform_ids = {**video.platform_ids, "youtube_id": publish_result.get("video_id")}

        elif platform == "tiktok":
            from app.services.publishing.tiktok_publisher import TikTokPublisher

            publisher = TikTokPublisher()
            tmp_path = tempfile.mktemp(suffix=".mp4")
            import httpx

            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.get(presigned_url)
                with open(tmp_path, "wb") as f:
                    f.write(resp.content)

            publish_result = await publisher.upload(
                access_token=connection.access_token,
                video_path=tmp_path,
                title=video.title,
                description=video.description,
            )
            video.platform_ids = {**video.platform_ids, "tiktok_id": publish_result.get("publish_id")}

        elif platform == "instagram":
            from app.services.publishing.instagram_publisher import InstagramPublisher

            publisher = InstagramPublisher()
            publish_result = await publisher.upload(
                access_token=connection.access_token,
                ig_user_id=connection.platform_user_id,
                video_url=presigned_url,
                caption=f"{video.title}\n\n{video.description}",
            )
            video.platform_ids = {**video.platform_ids, "instagram_id": publish_result.get("media_id")}

        # Aktualizuj status
        video.status = VideoStatus.PUBLISHED
        video.published_at = datetime.now(timezone.utc)
        db.add(video)

        if job:
            job.status = PublishStatus.PUBLISHED
            job.published_at = datetime.now(timezone.utc)
            job.platform_url = publish_result.get("url")
            job.platform_content_id = publish_result.get("video_id") or publish_result.get("publish_id") or publish_result.get("media_id")
            db.add(job)

        await db.commit()
        logger.info("Publikacja zakończona", video_id=video_id, platform=platform)


async def _update_publish_job(video_id: str, platform: str, status: str, error: str):
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.models.publish_job import PublishJob

    async with async_session_factory() as db:
        result = await db.execute(
            select(PublishJob).where(
                PublishJob.video_id == uuid.UUID(video_id),
                PublishJob.platform == platform,
            )
        )
        job = result.scalar_one_or_none()
        if job:
            job.status = status
            job.error_message = error
            job.retry_count += 1
            db.add(job)
            await db.commit()
