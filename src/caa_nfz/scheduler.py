import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from caa_nfz.services import refresh_zones
from caa_nfz.settings import settings

log = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _run_refresh():
    """排程 job：執行 refresh_zones()。"""
    try:
        count = await refresh_zones()
        log.info("排程同步完成: %d 筆", count)
    except Exception:
        log.exception("排程同步失敗")


def start_scheduler():
    """啟動排程器，新增 interval job。"""
    scheduler.add_job(
        _run_refresh,
        "interval",
        minutes=settings.refresh_interval_minutes,
        id="refresh_zones",
        replace_existing=True,
    )
    scheduler.start()
    log.info("排程已啟動: 每 %d 分鐘同步一次", settings.refresh_interval_minutes)


def shutdown_scheduler():
    """關閉排程器。"""
    scheduler.shutdown(wait=False)
    log.info("排程已關閉")
