"""
Pipeline generacji wideo — główne zadanie Celery.
Ulepszenie: state machine z recovery + osobne etapy + idempotentność.
Pipeline: PENDING → GENERATING_HOOK → GENERATING_SCRIPT → GENERATING_VOICE
         → FETCHING_MEDIA → RENDERING → READY_FOR_REVIEW
"""

import asyncio
import os
import tempfile
import uuid

import structlog
from celery import shared_task

from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


def _run_async(coro):
    """Helper do uruchamiania async w Celery (sync worker)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="app.tasks.video_pipeline.generate_video_task",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def generate_video_task(
    self,
    video_id: str,
    series_id: str,
    custom_topic: str | None = None,
    custom_prompt: str | None = None,
):
    """
    Główne zadanie generacji wideo — orkiestruje cały pipeline.
    Każdy etap aktualizuje status w bazie (state machine).
    """
    logger.info("Pipeline start", video_id=video_id, series_id=series_id)

    try:
        _run_async(_execute_pipeline(video_id, series_id, custom_topic, custom_prompt))
    except Exception as exc:
        logger.error("Pipeline błąd", video_id=video_id, error=str(exc))
        _run_async(_set_video_status(video_id, "failed", str(exc)))
        raise self.retry(exc=exc) if self.request.retries < self.max_retries else None


async def _execute_pipeline(
    video_id: str,
    series_id: str,
    custom_topic: str | None,
    custom_prompt: str | None,
):
    """Sekwencyjne wykonanie pipeline'u generacji."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.core.config import get_settings
    from app.models.series import Series
    from app.models.video import Video, VideoStatus
    from app.services.hooks.hook_optimizer import generate_hooks
    from app.services.llm.script_generator import generate_script
    from app.services.media.stock_provider import find_media_for_scenes
    from app.services.tts.tts_service import synthesize_with_fallback
    from app.services.video.renderer import VideoRenderer
    from app.services.video.storage import StorageService

    settings = get_settings()
    local_engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
    local_session_factory = async_sessionmaker(
        local_engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        async with local_session_factory() as db:
            # Pobierz dane
            video_result = await db.execute(select(Video).where(Video.id == uuid.UUID(video_id)))
            video = video_result.scalar_one()

            series_result = await db.execute(select(Series).where(Series.id == uuid.UUID(series_id)))
            series = series_result.scalar_one()

            topic = custom_topic or series.topic
            work_dir = tempfile.mkdtemp(prefix=f"autoshorts_{video_id[:8]}_")

            # ── Etap 1: Generowanie hooka ──
            video.status = VideoStatus.GENERATING_HOOK
            db.add(video)
            await db.commit()

            logger.info("Etap 1: Hook", video_id=video_id)
            hooks_data = await generate_hooks(topic, series.language)
            best_hook = hooks_data.get("best_hook", "")
            video.hook_text = best_hook

            # ── Etap 2: Generowanie skryptu ──
            video.status = VideoStatus.GENERATING_SCRIPT
            db.add(video)
            await db.commit()

            logger.info("Etap 2: Skrypt LLM", video_id=video_id)
            script_data = await generate_script(
                topic=topic,
                language=series.language,
                tone=series.tone,
                duration_seconds=series.target_duration_seconds,
                custom_prompt=custom_prompt,
                prompt_template=series.prompt_template,
            )

            video.title = script_data.get("title", f"Odcinek {video.episode_number}")
            video.script = _build_full_script(best_hook, script_data)
            video.description = script_data.get("description", "")
            video.tags = script_data.get("tags", [])

            # Przygotuj sceny
            scenes = []
            if best_hook:
                scenes.append({
                    "text": best_hook,
                    "visual_description": "dramatic attention-grabbing visual",
                    "duration_hint": "3",
                })
            scenes.extend(script_data.get("scenes", []))
            if script_data.get("call_to_action"):
                scenes.append({
                    "text": script_data["call_to_action"],
                    "visual_description": "subscribe follow button animation",
                    "duration_hint": "3",
                })

            # ── Etap 3: TTS ──
            video.status = VideoStatus.GENERATING_VOICE
            db.add(video)
            await db.commit()

            logger.info("Etap 3: TTS", video_id=video_id)
            full_narration = " ".join(s["text"] for s in scenes if s.get("text"))
            audio_bytes = await synthesize_with_fallback(
                text=full_narration,
                provider_name=series.tts_provider,
                voice_id=series.voice_id,
            )

            audio_path = os.path.join(work_dir, "narration.mp3")
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)

            # Upload audio do S3
            storage = StorageService()
            audio_key = storage.generate_key(f"audio/{series_id}", "mp3")
            voice_url = storage.upload_file(audio_path, audio_key, "audio/mpeg")
            video.voice_url = voice_url

            # ── Etap 4: Pobieranie mediów ──
            video.status = VideoStatus.FETCHING_MEDIA
            db.add(video)
            await db.commit()

            logger.info("Etap 4: Media stockowe", video_id=video_id, scenes_count=len(scenes))
            enriched_scenes = await find_media_for_scenes(scenes)
            video.scenes = enriched_scenes

            # ── Etap 5: Rendering ──
            video.status = VideoStatus.RENDERING
            db.add(video)
            await db.commit()

            logger.info("Etap 5: Rendering FFmpeg", video_id=video_id)
            renderer = VideoRenderer(work_dir=work_dir)
            output_path = await renderer.render(
                audio_path=audio_path,
                scenes=enriched_scenes,
                visual_style=series.visual_style,
                branding_text=series.visual_style.get("branding_text", ""),
            )

            # Upload wideo do S3
            video_key = storage.generate_key(f"videos/{series_id}", "mp4")
            video_url = storage.upload_file(output_path, video_key, "video/mp4")
            video.video_url = video_url

            # ── Gotowe ──
            video.status = VideoStatus.READY_FOR_REVIEW
            video.media_assets = {
                "images": [s.get("media_url") for s in enriched_scenes if s.get("media_url")],
                "clips": [],
                "music_track": None,
            }
            db.add(video)
            await db.commit()

            logger.info(
                "Pipeline zakończony pomyślnie",
                video_id=video_id,
                title=video.title,
                video_url=video_url,
            )

            # Cleanup
            import shutil
            shutil.rmtree(work_dir, ignore_errors=True)
    finally:
        await local_engine.dispose()


async def _set_video_status(video_id: str, status: str, error_msg: str | None = None):
    """Aktualizuje status wideo w bazie (error recovery)."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.core.config import get_settings
    from app.models.video import Video

    settings = get_settings()
    local_engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
    local_session_factory = async_sessionmaker(
        local_engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        async with local_session_factory() as db:
            result = await db.execute(select(Video).where(Video.id == uuid.UUID(video_id)))
            video = result.scalar_one_or_none()
            if video:
                video.status = status
                video.error_message = error_msg
                db.add(video)
                await db.commit()
    finally:
        await local_engine.dispose()


def _build_full_script(hook: str, script_data: dict) -> str:
    """Składa pełny skrypt z hooka, scen i CTA."""
    parts = []
    if hook:
        parts.append(f"[HOOK] {hook}")
    for i, scene in enumerate(script_data.get("scenes", []), 1):
        parts.append(f"[SCENA {i}] {scene.get('text', '')}")
    cta = script_data.get("call_to_action", "")
    if cta:
        parts.append(f"[CTA] {cta}")
    return "\n\n".join(parts)
