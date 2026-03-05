# Scope 7: Refresh API 與設定補齊

## 目標

新增 `POST /zones/refresh` endpoint 供手動觸發資料同步，並以 Bearer Token 驗證保護。同時補齊 `settings.py` 中 API 相關設定欄位。

## 修改既有檔案

### `src/caa_nfz/settings.py` — 新增欄位

```diff
 class Settings(BaseSettings):
     ...
+    api_prefix: str = "/api"
+    refresh_token: str = ""
```

| 欄位 | 環境變數 | 預設值 | 說明 |
|------|----------|--------|------|
| `api_prefix` | `API_PREFIX` | `"/api"` | 路由前綴 |
| `refresh_token` | `REFRESH_TOKEN` | `""` | refresh endpoint 驗證用 token，空字串表示未設定 |

### `src/caa_nfz/routes.py` — 新增 refresh endpoint

```python
import hmac

from fastapi import APIRouter, HTTPException, Header

from caa_nfz.services import refresh_zones
from caa_nfz.settings import settings

router = APIRouter()


# ... 既有 GET /zones 和 POST /zones/check 保持不變 ...


@router.post("/zones/refresh", include_in_schema=False)
async def post_refresh_zones(
    authorization: str = Header(default=""),
):
    """手動觸發禁航區資料同步（需 Bearer Token）。"""
    expected = f"Bearer {settings.refresh_token}"
    if not settings.refresh_token or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")
    count = await refresh_zones()
    return {"message": "同步完成", "count": count}
```

重點：
- `include_in_schema=False` — 從 OpenAPI 文件隱藏此 endpoint
- Token 比對使用 `Bearer {token}` 格式
- `refresh_token` 為空字串時一律回 401，避免未設定時被任意存取
- 使用 `hmac.compare_digest()` 做 constant-time 比對，防止 timing attack 透過回應時間差推測 token 內容
- 背景執行與 lock 保護見 Scope 9

## 驗證步驟

### 1. 帶正確 token 呼叫

```bash
export REFRESH_TOKEN="my-secret-token"
# 啟動伺服器後...
curl -X POST http://localhost:8000/api/zones/refresh \
  -H "Authorization: Bearer my-secret-token"
```

預期回傳：

```json
{"message": "同步完成", "count": 123}
```

### 2. 不帶 token 呼叫

```bash
curl -X POST http://localhost:8000/api/zones/refresh
```

預期回傳 HTTP 401：

```json
{"detail": "Unauthorized"}
```

### 3. 帶錯誤 token 呼叫

```bash
curl -X POST http://localhost:8000/api/zones/refresh \
  -H "Authorization: Bearer wrong-token"
```

預期回傳 HTTP 401：

```json
{"detail": "Unauthorized"}
```

### 4. OpenAPI 文件確認

瀏覽 `http://localhost:8000/docs`，確認只顯示 2 個 endpoints（`GET /zones` 和 `POST /zones/check`），**不包含** `POST /zones/refresh`。
