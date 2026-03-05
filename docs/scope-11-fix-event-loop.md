# Scope 11: 修復背景同步 event loop 衝突

## 目標

修復 `refresh_zones()` 在背景執行時因 event loop 不匹配導致的 RuntimeError。

## 問題背景

`database.py` 的 `engine`（asyncpg 連線池）綁定 uvicorn 的 main event loop。
但 `routes.py` 和 `scheduler.py` 都在獨立 thread 中呼叫 `asyncio.run(refresh_zones())`，
建立了新的 event loop，導致 asyncpg 拋出：

```
RuntimeError: Task got Future attached to a different loop
```

受影響的位置：
- `src/caa_nfz/routes.py:82` — `_run_refresh()` 用 `asyncio.run()`
- `src/caa_nfz/scheduler.py:17` — `_run_refresh()` 用 `asyncio.run()`

核心問題：`fetch_layer()`（`crawler.py:11`）是同步阻塞的 HTTP 請求，
不能直接在 main loop 上跑（會卡住所有 API），但 DB 操作又必須在 main loop 上執行。

## 修改既有檔案

### `src/caa_nfz/services.py` — 拆分 sync 爬蟲與 async DB 寫入

將 `refresh_zones()` 改為：
1. 用 `run_in_executor` 在 thread pool 執行同步爬蟲 `fetch_all_layers()`
2. 拿到資料後，回到 main loop 用 async session 寫 DB

```python
import asyncio
import json
import logging

from sqlalchemy import delete

from caa_nfz.config import LAYERS
from caa_nfz.converter import _arcgis_geometry_to_geojson
from caa_nfz.crawler import fetch_all_layers
from caa_nfz.database import async_session
from caa_nfz.models import NoFlyZone

log = logging.getLogger(__name__)

BATCH_SIZE = 500


async def refresh_zones() -> int:
    """爬取所有圖層，全量替換資料庫中的資料。回傳寫入筆數。"""
    loop = asyncio.get_running_loop()
    all_layers = await loop.run_in_executor(None, fetch_all_layers)

    total = 0
    async with async_session() as session, session.begin():
        await session.execute(delete(NoFlyZone))

        batch: list[NoFlyZone] = []
        for layer_name, features in all_layers.items():
            cfg = LAYERS[layer_name]
            name_field = cfg.get("name_field")

            for f in features:
                attrs = f.get("attributes", {})
                geojson_geom = _arcgis_geometry_to_geojson(f.get("geometry", {}))
                if geojson_geom is None:
                    continue

                batch.append(
                    NoFlyZone(
                        layer=layer_name,
                        name=attrs.get(name_field) if name_field else None,
                        properties=json.dumps(attrs, ensure_ascii=False),
                        geometry=f"SRID=4326;{json.dumps(geojson_geom)}",
                    )
                )

                if len(batch) >= BATCH_SIZE:
                    session.add_all(batch)
                    await session.flush()
                    total += len(batch)
                    batch.clear()

        if batch:
            session.add_all(batch)
            await session.flush()
            total += len(batch)

    log.info("refresh_zones 完成: 寫入 %d 筆", total)
    return total
```

重點：
- `fetch_all_layers()`（`crawler.py:53`）已存在，回傳 `dict[str, list[dict]]`
- `run_in_executor(None, ...)` 在預設 thread pool 執行，不阻塞 event loop
- DB 寫入在 main loop 上 async 執行，不會有 loop 衝突
- 移除 `from caa_nfz.crawler import fetch_layer`，改用 `fetch_all_layers`

### `src/caa_nfz/routes.py` — 改用 `asyncio.create_task`

```python
import asyncio
import hmac
import json
import logging

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from caa_nfz.database import async_session
from caa_nfz.models import NoFlyZone
from caa_nfz.services import refresh_zones
from caa_nfz.settings import settings

router = APIRouter()
log = logging.getLogger(__name__)
_refresh_running = False


# ... 既有 GET /zones 和 POST /zones/check 保持不變 ...


async def _run_refresh() -> None:
    """背景執行 refresh_zones()，完成後重設 flag。"""
    global _refresh_running
    try:
        count = await refresh_zones()
        log.info("背景同步完成，共 %d 筆", count)
    except Exception:
        log.exception("背景同步失敗")
    finally:
        _refresh_running = False


@router.post("/zones/refresh", include_in_schema=False)
async def post_refresh_zones(
    authorization: str = Header(default=""),
):
    """手動觸發禁航區資料同步（需 Bearer Token）。"""
    global _refresh_running
    expected = f"Bearer {settings.admin_token}"
    if not settings.admin_token or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if _refresh_running:
        raise HTTPException(status_code=409, detail="同步正在執行中")

    _refresh_running = True
    asyncio.create_task(_run_refresh())
    return {"message": "同步已排入背景執行"}
```

重點：
- 移除 `import threading` 和 `_refresh_lock`
- `_refresh_running` flag 在單一 event loop 中天然 thread-safe（無需 lock）
- `asyncio.create_task()` 在 main loop 上排程，`refresh_zones()` 內的 sync 爬蟲已由 `run_in_executor` 處理

### `src/caa_nfz/scheduler.py` — 改用 `asyncio.run_coroutine_threadsafe`

```python
import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from caa_nfz.services import refresh_zones
from caa_nfz.settings import settings

log = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
_main_loop: asyncio.AbstractEventLoop | None = None


def _run_refresh():
    """在 scheduler thread 中，將 refresh_zones() 提交到 main event loop 執行。"""
    if _main_loop is None or _main_loop.is_closed():
        log.error("main event loop 不可用，跳過排程同步")
        return
    try:
        future = asyncio.run_coroutine_threadsafe(refresh_zones(), _main_loop)
        count = future.result()
        log.info("排程同步完成: %d 筆", count)
    except Exception:
        log.exception("排程同步失敗")


def start_scheduler():
    """啟動排程器，新增 interval job。"""
    global _main_loop
    _main_loop = asyncio.get_running_loop()
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

重點：
- `start_scheduler()` 在 `lifespan()` 中被呼叫（async context），可取得 main loop
- `_run_refresh()` 在 scheduler thread 中，用 `run_coroutine_threadsafe()` 將 coroutine 提交到 main loop
- `future.result()` 阻塞等待完成（在 scheduler thread 中阻塞沒問題）
- 不再建立新 event loop，所有 async 操作都在 main loop 上

## 驗證步驟

### 1. Lint 檢查

```bash
pdm run ruff check src/caa_nfz/services.py src/caa_nfz/routes.py src/caa_nfz/scheduler.py
```

### 2. 手動觸發 refresh

```bash
curl -X POST http://localhost:8000/api/zones/refresh \
  -H "Authorization: Bearer my-secret-token"
```

預期：回傳 `{"message": "同步已排入背景執行"}`，server log 顯示同步完成、無 RuntimeError。

### 3. 同步期間 API 不阻塞

同步進行中呼叫 `GET /api/zones`，應正常回應。

### 4. 排程同步

等待排程觸發（或暫時調短 `refresh_interval_minutes`），確認 log 顯示排程同步完成。
