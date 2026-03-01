"""
Główna aplikacja FastAPI — AutoShorts MVP.
Ulepszenia: structured logging, CORS, rate limiting, Sentry, health checks.
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import close_db, init_db

settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle — inicjalizacja i zamknięcie zasobów."""
    logger.info("Uruchamianie AutoShorts API", version=settings.APP_VERSION)

    if settings.ENVIRONMENT == "development":
        await init_db()

    # Sentry
    if settings.SENTRY_DSN:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(dsn=settings.SENTRY_DSN, integrations=[FastApiIntegration()])

    yield

    await close_db()
    logger.info("AutoShorts API zamknięte")


# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API do automatycznego generowania i publikacji faceless short-video",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Rate limiting — limiter musi być w state przed middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# SlowAPIMiddleware egzekwuje default_limits globalnie (bez niego limiter działa tylko per-dekorator)
app.add_middleware(SlowAPIMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ── Health Checks ──

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/health/ready")
async def readiness_check():
    """Sprawdzenie gotowości (baza danych + Redis). Zwraca 503 przy awarii zależności."""
    import redis.asyncio as aioredis
    from sqlalchemy import text

    from app.core.database import engine

    errors: list[str] = []

    # Sprawdź bazę danych
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        errors.append(f"database: {exc}")

    # Sprawdź Redis
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
    except Exception as exc:
        errors.append(f"redis: {exc}")

    if errors:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "errors": errors},
        )

    return {"status": "ready"}


# ── Global exception handler ──

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Nieobsłużony wyjątek", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Wewnętrzny błąd serwera"},
    )
