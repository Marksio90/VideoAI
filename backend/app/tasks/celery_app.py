"""
Konfiguracja Celery — kolejka zadań.
Ulepszenie: osobne kolejki per typ zadania + priorytetyzacja.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "autoshorts",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Retry
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,

    # Routing — osobne kolejki dla różnych typów zadań
    task_routes={
        "app.tasks.video_pipeline.*": {"queue": "video_pipeline"},
        "app.tasks.publishing.*": {"queue": "publishing"},
        "app.tasks.scheduler.*": {"queue": "scheduler"},
        "app.tasks.analytics.*": {"queue": "analytics"},
    },

    # Beat schedule — harmonogram cron
    beat_schedule={
        "check-scheduled-videos": {
            "task": "app.tasks.scheduler.check_scheduled_videos",
            "schedule": 60.0,  # co minutę
        },
        "refresh-platform-tokens": {
            "task": "app.tasks.scheduler.refresh_expiring_tokens",
            "schedule": 3600.0,  # co godzinę
        },
        "sync-analytics": {
            "task": "app.tasks.analytics.sync_all_metrics",
            "schedule": 21600.0,  # co 6 godzin
        },
        "reset-monthly-counters": {
            "task": "app.tasks.scheduler.reset_monthly_counters",
            "schedule": 86400.0,  # co 24h (sprawdza czy jest 1. dzień miesiąca)
        },
    },

    # Timeouts
    task_soft_time_limit=600,  # 10 min soft limit
    task_time_limit=900,  # 15 min hard limit
)

# Explicitly include task modules (autodiscover_tasks looks for a "tasks"
# submodule inside each listed package, which doesn't match our layout).
celery_app.conf.update(
    include=[
        "app.tasks.video_pipeline",
        "app.tasks.publishing",
        "app.tasks.scheduler",
        "app.tasks.analytics",
    ],
)
