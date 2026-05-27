from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services import (
    daily_morning_newsletter_job,
    refresh_daily_shifts_async,
)
from db import reset_weekly_gratitude_limits_async
from .announcement_scheduler import run_announcements_async


def setup_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    scheduler.add_job(
        daily_morning_newsletter_job,
        trigger="cron",
        hour=10,
        minute=00
    )

    scheduler.add_job(
        refresh_daily_shifts_async,
        trigger="cron",
        hour=5,
        minute=00
    )

    scheduler.add_job(
        reset_weekly_gratitude_limits_async,
        trigger="cron",
        day_of_week="mon",
        hour=5,
        minute=10
    )

    scheduler.add_job(
        run_announcements_async,
        trigger="interval",
        minutes=1
    )
    
    return scheduler