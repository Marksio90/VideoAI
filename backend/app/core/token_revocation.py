"""
Serwis unieważniania tokenów JWT (JTI blacklist) — przechowywanie w Redis.

Każdy refresh token ma unikalny JTI (JWT ID). Po użyciu (rotacja) JTI jest
zapisywany w Redis z TTL równym pozostałemu czasowi życia tokena.
Próba ponownego użycia tego samego refresh tokena zostanie odrzucona.
"""

from datetime import datetime, timezone

import structlog

logger = structlog.get_logger()

_REDIS_PREFIX = "revoked_jti:"


async def _get_redis():
    """Tworzy async Redis klienta z ustawień aplikacji."""
    import redis.asyncio as aioredis

    from app.core.config import get_settings

    settings = get_settings()
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def revoke_jti(jti: str, exp: int) -> None:
    """Zapisuje JTI w blackliście z TTL do wygaśnięcia tokena.

    Args:
        jti: identyfikator JWT (UUID hex)
        exp: timestamp wygaśnięcia tokena (Unix timestamp)
    """
    now = int(datetime.now(timezone.utc).timestamp())
    ttl = max(exp - now, 1)  # min 1 sekunda

    r = await _get_redis()
    try:
        await r.setex(f"{_REDIS_PREFIX}{jti}", ttl, "1")
        logger.debug("JTI unieważniony", jti=jti, ttl_seconds=ttl)
    finally:
        await r.aclose()


async def is_jti_revoked(jti: str) -> bool:
    """Sprawdza, czy JTI jest na blackliście.

    Returns:
        True jeśli token jest unieważniony (należy odrzucić), False jeśli OK.
    """
    r = await _get_redis()
    try:
        return await r.exists(f"{_REDIS_PREFIX}{jti}") > 0
    finally:
        await r.aclose()
