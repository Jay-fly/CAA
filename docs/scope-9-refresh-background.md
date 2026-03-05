# Scope 9: Refresh 背景執行與 Lock 保護

## 目標

將 refresh endpoint 從阻塞式改為背景執行，並加入 lock 防止重複觸發。

## 問題背景

Scope 7 的 refresh endpoint 使用 `await refresh_zones()` 阻塞等待同步完成才回應。
但 `refresh_zones()` 內部呼叫的 `fetch_layer()`（`src/caa_nfz/crawler.py:11`）是同步 HTTP 請求，
整個同步過程可能耗時很久，且會阻塞 event loop。

此外，若使用者連續呼叫 refresh API，會同時產生多個同步任務，造成 DB 衝突和外部 API 過載。

## 修改既有檔案

### `src/caa_nfz/routes.py`

```python
import asyncio
import hmac
import logging
import threading

from fastapi import APIRouter, HTTPException, Header

from caa_nfz.services import refresh_zones
from caa_nfz.settings import settings

log = logging.getLogger(__name__)
router = APIRouter()

_refresh_lock = threading.Lock()


def _run_refresh():
    """在獨立 thread 中執行 async refresh_zones()。"""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(refresh_zones())
    except Exception:
        log.exception("手動同步失敗")
    finally:
        loop.close()
        _refresh_lock.release()


# ... 既有 GET /zones 和 POST /zones/check 保持不變 ...


@router.post("/zones/refresh", include_in_schema=False)
async def post_refresh_zones(
    authorization: str = Header(default=""),
):
    """手動觸發禁航區資料同步（需 Bearer Token）。"""
    expected = f"Bearer {settings.refresh_token}"
    if not settings.refresh_token or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not _refresh_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="同步正在執行中")
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, _run_refresh)
    return {"message": "同步已排入背景執行"}
```

### 重點說明

- `run_in_executor(None, _run_refresh)` — 在預設 ThreadPoolExecutor 中開獨立 thread 執行，不阻塞 event loop
- `_run_refresh` 建立新 event loop（與 Scope 6 scheduler 相同策略），因為 `fetch_layer()` 是同步函式
- `threading.Lock` — `acquire(blocking=False)` 非阻塞嘗試取鎖，同一時間只允許一個同步任務
- 鎖在 `_run_refresh` 的 `finally` 中釋放，確保無論成功或失敗都會解鎖
- 重複呼叫回 409 Conflict

## 驗證步驟

### 1. 帶正確 token 呼叫

```bash
curl -X POST http://localhost:8000/api/zones/refresh \
  -H "Authorization: Bearer $REFRESH_TOKEN"
```

預期回傳：

```json
{"message": "同步已排入背景執行"}
```

### 2. 同步進行中再次呼叫

```bash
curl -X POST http://localhost:8000/api/zones/refresh \
  -H "Authorization: Bearer $REFRESH_TOKEN"
```

預期回傳 HTTP 409：

```json
{"detail": "同步正在執行中"}
```

### 3. Server log 確認

背景同步完成後，server log 應顯示同步結果或錯誤訊息。
