"""
Stock media provider — pobieranie zasobów wizualnych do scen wideo.
Używa Pexels API jako głównego dostawcy mediów stockowych.
Gdy brak klucza API, sceny są zwracane bez pola media_url (pipeline działa dalej).
"""

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

_PEXELS_API_BASE = "https://api.pexels.com/v1"


async def find_media_for_scenes(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Dla każdej sceny wyszukuje pasujące zdjęcie stockowe przez Pexels API.
    Zwraca sceny wzbogacone o pole 'media_url'.
    Gdy klucz API nie jest skonfigurowany, zwraca oryginalne sceny bez zmian.
    """
    from app.core.config import get_settings

    settings = get_settings()
    api_key = getattr(settings, "PEXELS_API_KEY", "")

    if not api_key:
        logger.warning("Brak PEXELS_API_KEY — sceny bez mediów stockowych")
        return scenes

    enriched: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=15) as client:
        for scene in scenes:
            query = (scene.get("visual_description") or scene.get("text", ""))[:80]
            media_url = await _search_pexels_photo(client, api_key, query)
            enriched.append({**scene, "media_url": media_url})

    return enriched


async def _search_pexels_photo(
    client: httpx.AsyncClient, api_key: str, query: str
) -> str | None:
    """Wyszukuje jedno zdjęcie portretowe z Pexels pasujące do opisu sceny."""
    if not query.strip():
        return None
    try:
        resp = await client.get(
            f"{_PEXELS_API_BASE}/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": 1, "orientation": "portrait"},
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if photos:
            return photos[0]["src"]["large2x"]
    except Exception as exc:
        logger.warning("Pexels błąd wyszukiwania", query=query, error=str(exc))
    return None
