"""Główny router API v1."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, series, videos, publishing, analytics, webhooks, users

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Autoryzacja"])
api_router.include_router(users.router, prefix="/users", tags=["Użytkownicy"])
api_router.include_router(series.router, prefix="/series", tags=["Serie"])
api_router.include_router(videos.router, prefix="/videos", tags=["Wideo"])
api_router.include_router(publishing.router, prefix="/publishing", tags=["Publikacja"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analityka"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
