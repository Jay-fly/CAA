# Scope 6: 定時排程

## 目標

建立 `scheduler.py`，使用 APScheduler 定時執行 `refresh_zones()`。

## 新增檔案

### `src/caa_nfz/scheduler.py`

```python
import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from caa_nfz.services import refresh_zones
from caa_nfz.settings import settings

log = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _run_refresh():
    """在背景 thread 中執行 async refresh_zones()。"""
    loop = asyncio.new_event_loop()
    try:
        count = loop.run_until_complete(refresh_zones())
        log.info("排程同步完成: %d 筆", count)
    except Exception:
        log.exception("排程同步失敗")
    finally:
        loop.close()


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
```

## 設計說明

- 使用 `BackgroundScheduler`（非 async scheduler），在獨立 thread 執行，避免阻塞 FastAPI event loop
- `_run_refresh()` 建立新的 event loop 來執行 async `refresh_zones()`
- interval 間隔由 `settings.refresh_interval_minutes` 控制，預設 60 分鐘
- `replace_existing=True` 確保重複啟動不會建立多個同名 job

## 與 App 整合

排程器的 `start_scheduler()` / `shutdown_scheduler()` 將在 Scope 7 的 FastAPI lifespan 中呼叫：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()
```

## 驗證

設定較短的 interval 進行測試：

```bash
CAA_REFRESH_INTERVAL_MINUTES=1 pdm run uvicorn caa_nfz.app:app
```

觀察 log 是否每分鐘執行一次同步。
