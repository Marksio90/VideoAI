"""
Endpointy CRUD serii wideo.
Ulepszenie: sprawdzanie limitów planu + paginacja + soft-delete.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PaginationParams, get_current_user
from app.core.database import get_db
from app.models.series import Series
from app.models.user import User
from app.schemas.series import (
    SeriesCreateRequest,
    SeriesListResponse,
    SeriesResponse,
    SeriesUpdateRequest,
)

router = APIRouter()


@router.get("", response_model=SeriesListResponse)
async def list_series(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista serii użytkownika z paginacją."""
    base_query = select(Series).where(
        Series.user_id == current_user.id,
        Series.deleted_at.is_(None),
    )

    count_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = count_result.scalar() or 0

    result = await db.execute(
        base_query.order_by(Series.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    items = list(result.scalars().all())

    return SeriesListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("", response_model=SeriesResponse, status_code=status.HTTP_201_CREATED)
async def create_series(
    body: SeriesCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tworzenie nowej serii. Sprawdza limit planu."""
    # Sprawdzenie limitu serii
    count_result = await db.execute(
        select(func.count()).select_from(
            select(Series)
            .where(Series.user_id == current_user.id, Series.deleted_at.is_(None))
            .subquery()
        )
    )
    current_count = count_result.scalar() or 0

    if current_count >= current_user.max_series:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Osiągnięto limit serii ({current_user.max_series}). Ulepsz plan, aby tworzyć więcej.",
        )

    series = Series(
        user_id=current_user.id,
        title=body.title,
        description=body.description,
        topic=body.topic,
        language=body.language,
        tone=body.tone,
        target_duration_seconds=body.target_duration_seconds,
        schedule_config=body.schedule_config.model_dump(),
        publish_channels=body.publish_channels.model_dump(),
        visual_style=body.visual_style.model_dump(),
        voice_id=body.voice_id,
        tts_provider=body.tts_provider,
    )
    if body.prompt_template:
        series.prompt_template = body.prompt_template

    db.add(series)
    await db.flush()
    return series


@router.get("/{series_id}", response_model=SeriesResponse)
async def get_series(
    series_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pobranie szczegółów serii."""
    result = await db.execute(
        select(Series).where(
            Series.id == series_id,
            Series.user_id == current_user.id,
            Series.deleted_at.is_(None),
        )
    )
    series = result.scalar_one_or_none()
    if not series:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seria nie znaleziona")
    return series


@router.patch("/{series_id}", response_model=SeriesResponse)
async def update_series(
    series_id: uuid.UUID,
    body: SeriesUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aktualizacja serii."""
    result = await db.execute(
        select(Series).where(
            Series.id == series_id,
            Series.user_id == current_user.id,
            Series.deleted_at.is_(None),
        )
    )
    series = result.scalar_one_or_none()
    if not series:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seria nie znaleziona")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            if hasattr(value, "model_dump"):
                value = value.model_dump()
            setattr(series, field, value)

    db.add(series)
    await db.flush()
    return series


@router.delete("/{series_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_series(
    series_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete serii."""
    from datetime import datetime, timezone

    result = await db.execute(
        select(Series).where(
            Series.id == series_id,
            Series.user_id == current_user.id,
            Series.deleted_at.is_(None),
        )
    )
    series = result.scalar_one_or_none()
    if not series:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seria nie znaleziona")

    series.deleted_at = datetime.now(timezone.utc)
    series.is_active = False
    db.add(series)
    await db.flush()
