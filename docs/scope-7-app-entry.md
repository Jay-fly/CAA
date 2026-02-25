# Scope 7: 應用程式入口

## 目標

建立 `app.py` 作為 FastAPI 應用入口，整合 database init、scheduler、routes。更新 pyproject.toml entry point。

## 新增檔案

### `src/caa_nfz/app.py`

```python
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from caa_nfz.database import init_db
from caa_nfz.routes import router
from caa_nfz.scheduler import shutdown_scheduler, start_scheduler
from caa_nfz.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()


app = FastAPI(
    title="CAA 禁限航區 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router, prefix=settings.api_prefix)
```

## 修改既有檔案

### `pyproject.toml` — 更新 entry point

```diff
 [project.scripts]
-caa-nfz = "caa_nfz.crawler:main"
+caa-nfz = "caa_nfz.app:app"
```

> 注意：此 entry point 是給 `pdm run` 等工具參考。實際啟動使用 uvicorn。

## Lifespan 流程

```
App 啟動
  ├── init_db()        → 建立資料表（若不存在）
  └── start_scheduler() → 啟動定時同步 job
      ...
App 關閉
  └── shutdown_scheduler() → 停止排程器
```

## 啟動方式

```bash
# 開發模式
pdm run uvicorn caa_nfz.app:app --reload --host 0.0.0.0 --port 8000

# 或直接
uvicorn caa_nfz.app:app --reload
```

## 驗證步驟

### 1. 啟動確認

```bash
pdm run uvicorn caa_nfz.app:app --host 0.0.0.0 --port 8000
```

應看到：
- `排程已啟動: 每 60 分鐘同步一次`
- Uvicorn running on `http://0.0.0.0:8000`

### 2. OpenAPI 文件

瀏覽 `http://localhost:8000/docs`，確認三個 endpoints 列出。

### 3. 手動同步

```bash
curl -X POST http://localhost:8000/api/zones/refresh
```

確認回傳 `{"message": "同步完成", "count": N}`。

### 4. 查詢資料

```bash
curl http://localhost:8000/api/zones | python -m json.tool
```

### 5. 座標檢查

```bash
curl -X POST http://localhost:8000/api/zones/check \
  -H "Content-Type: application/json" \
  -d '{"lng": 121.5654, "lat": 25.0330}'
```
