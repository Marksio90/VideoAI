"""
Wymiana kodów OAuth na tokeny dla platform (YouTube, TikTok, Instagram).
"""

from datetime import datetime, timedelta, timezone

import httpx
import structlog

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


async def exchange_oauth_code(platform: str, auth_code: str, redirect_uri: str) -> dict:
    """Wymienia authorization code na access+refresh tokeny."""
    if platform == "youtube":
        return await _exchange_youtube(auth_code, redirect_uri)
    elif platform == "tiktok":
        return await _exchange_tiktok(auth_code, redirect_uri)
    elif platform == "instagram":
        return await _exchange_instagram(auth_code, redirect_uri)
    else:
        raise ValueError(f"Nieznana platforma: {platform}")


async def _exchange_youtube(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.YOUTUBE_CLIENT_ID,
                "client_secret": settings.YOUTUBE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600)),
            "user_id": None,
            "username": None,
            "channel_name": None,
        }


async def _exchange_tiktok(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key": settings.TIKTOK_CLIENT_KEY,
                "client_secret": settings.TIKTOK_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 86400)),
            "user_id": data.get("open_id"),
            "username": None,
            "channel_name": None,
        }


async def _exchange_instagram(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Krok 1: krótkotrwały token
        resp = await client.post(
            "https://api.instagram.com/oauth/access_token",
            data={
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        resp.raise_for_status()
        short_data = resp.json()

        # Krok 2: wymiana na długotrwały token
        resp2 = await client.get(
            "https://graph.instagram.com/access_token",
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": settings.META_APP_SECRET,
                "access_token": short_data["access_token"],
            },
        )
        resp2.raise_for_status()
        long_data = resp2.json()

        return {
            "access_token": long_data["access_token"],
            "refresh_token": None,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=long_data.get("expires_in", 5184000)),
            "user_id": str(short_data.get("user_id")),
            "username": None,
            "channel_name": None,
        }
