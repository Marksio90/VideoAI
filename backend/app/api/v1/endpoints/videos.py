"""
Endpointy wideo — CRUD, generowanie, zatwierdzanie.
Ulepszenie: walidacja state machine + rate limiting generacji.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PaginationParams, get_current_user
from app.core.database import get_db
from app.models.series import Series
from app.models.video import Video, VideoStatus
from app.models.user import User
from app.schemas.video import (
    VideoApproveRequest,
    VideoGenerateRequest,
    VideoListResponse,
    VideoResponse,
    VideoUpdateRequest,
)

router = APIRouter()


@router.get("", response_model=VideoListResponse)
async def list_videos(
    series_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista wideo użytkownika z filtrami."""
    base_query = (
        select(Video)
        .join(Series, Video.series_id == Series.id)
        .where(Series.user_id == current_user.id)
    )

    if series_id:
        base_query = base_query.where(Video.series_id == series_id)
    if status_filter:
        base_query = base_query.where(Video.status == status_filter)

    count_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = count_result.scalar() or 0

    result = await db.execute(
        base_query.order_by(Video.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    items = list(result.scalars().all())

    return VideoListResponse(
        items=items, total=total, page=pagination.page, page_size=pagination.page_size
    )


@router.post("/generate", response_model=VideoResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_video(
    body: VideoGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Uruchomienie automatycznej generacji wideo.
    Tworzy rekord Video w statusie PENDING i wysyła zadanie do kolejki.
    """
    # Walidacja serii
    result = await db.execute(
        select(Series).where(
            Series.id == body.series_id,
            Series.user_id == current_user.id,
            Series.deleted_at.is_(None),
        )
    )
    series = result.scalar_one_or_none()
    if not series:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seria nie znaleziona")

    # Sprawdzenie limitu miesięcznego
    if current_user.videos_generated_this_month >= current_user.max_videos_per_month:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Osiągnięto miesięczny limit wideo ({current_user.max_videos_per_month}). Ulepsz plan.",
        )

    # Tworzenie rekordu wideo
    video = Video(
        series_id=series.id,
        episode_number=series.total_episodes + 1,
        status=VideoStatus.PENDING,
    )
    db.add(video)

    series.total_episodes += 1
    current_user.videos_generated_this_month += 1
    db.add(series)
    db.add(current_user)
    await db.flush()

    # Wysłanie zadania do Celery
    from app.tasks.video_pipeline import generate_video_task

    generate_video_task.delay(
        str(video.id),
        str(series.id),
        body.custom_topic,
        body.custom_prompt,
    )

    return video


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pobranie szczegółów wideo."""
    result = await db.execute(
        select(Video)
        .join(Series, Video.series_id == Series.id)
        .where(Video.id == video_id, Series.user_id == current_user.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wideo nie znalezione")
    return video


@router.patch("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: uuid.UUID,
    body: VideoUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Edycja wideo (skrypt, tytuł, opis, tagi)."""
    result = await db.execute(
        select(Video)
        .join(Series, Video.series_id == Series.id)
        .where(Video.id == video_id, Series.user_id == current_user.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wideo nie znalezione")

    # Edycja dozwolona tylko w stanach: ready_for_review, approved
    editable_statuses = {VideoStatus.READY_FOR_REVIEW, VideoStatus.APPROVED}
    if video.status not in editable_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Edycja niedostępna w stanie '{video.status}'",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(video, field, value)
    db.add(video)
    await db.flush()
    return video


@router.post("/{video_id}/approve", response_model=VideoResponse)
async def approve_video(
    video_id: uuid.UUID,
    body: VideoApproveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Zatwierdzenie wideo do publikacji."""
    result = await db.execute(
        select(Video)
        .join(Series, Video.series_id == Series.id)
        .where(Video.id == video_id, Series.user_id == current_user.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wideo nie znalezione")

    if video.status != VideoStatus.READY_FOR_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Zatwierdzenie możliwe tylko ze stanu 'ready_for_review', aktualny: '{video.status}'",
        )

    video.status = VideoStatus.APPROVED
    if body.scheduled_publish_at:
        video.scheduled_publish_at = body.scheduled_publish_at

    db.add(video)
    await db.flush()

    # Jeśli podano kanały publikacji — twórz zadania publikacji
    if body.publish_channels:
        from app.tasks.publishing import schedule_publish_task

        schedule_publish_task.delay(str(video.id), body.publish_channels)

    return video


@router.post("/{video_id}/regenerate", response_model=VideoResponse, status_code=status.HTTP_202_ACCEPTED)
async def regenerate_video(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ponowna generacja wideo (po błędzie lub odrzuceniu)."""
    result = await db.execute(
        select(Video)
        .join(Series, Video.series_id == Series.id)
        .where(Video.id == video_id, Series.user_id == current_user.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wideo nie znalezione")

    regenerable = {VideoStatus.FAILED, VideoStatus.READY_FOR_REVIEW, VideoStatus.CANCELLED}
    if video.status not in regenerable:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ponowna generacja niedostępna w stanie '{video.status}'",
        )

    video.status = VideoStatus.PENDING
    video.error_message = None
    video.retry_count += 1
    db.add(video)
    await db.flush()

    from app.tasks.video_pipeline import generate_video_task

    generate_video_task.delay(str(video.id), str(video.series_id), None, None)

    return video
