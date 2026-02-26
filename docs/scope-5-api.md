# Scope 5: API 路由

## 目標

建立 `routes.py`，提供三個 API endpoints。

## 新增檔案

### `src/caa_nfz/routes.py`

```python
from pydantic import BaseModel
from fastapi import APIRouter, Query
from sqlalchemy import func, select

from caa_nfz.database import async_session
from caa_nfz.models import NoFlyZone
from caa_nfz.services import refresh_zones

router = APIRouter()


class CheckPointRequest(BaseModel):
    lng: float
    lat: float


@router.get("/zones")
async def get_zones(layer: str | None = Query(None)):
    ...


@router.post("/zones/check")
async def check_point(body: CheckPointRequest):
    ...


@router.post("/zones/refresh")
async def trigger_refresh():
    ...
```

## Endpoints 規格

### 1. `GET /api/zones`

查詢所有禁限航區，支援依圖層篩選。

**Query Parameters：**

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `layer` | `str` | 否 | 圖層名稱篩選（例如 `UAV`） |

**Response（200）：**

```json
{
  "count": 42,
  "zones": [
    {
      "id": 1,
      "layer": "UAV",
      "name": "松山機場",
      "properties": { ... },
      "geometry": { "type": "Polygon", "coordinates": [...] },
      "created_at": "2025-01-01T00:00:00+08:00"
    }
  ]
}
```

**實作要點：**
- 使用 `func.ST_AsGeoJSON(NoFlyZone.geometry)` 將 PostGIS geometry 轉為 GeoJSON
- `ST_AsGeoJSON()` 回傳的是 JSON **字串**，需 `json.loads()` 解析為 dict
- `properties` 欄位從 JSON string 解析回 dict（同樣需 `json.loads()`）
- 若提供 `layer` 參數，加上 `WHERE layer = :layer` 篩選

**效能備註：**
- 全部資料（5 圖層、~4,845 筆）原始 JSON 約 27 MB，GZip 壓縮後約 8 MB
- 在 Scope 7 的 FastAPI app 加上 `GZipMiddleware`，瀏覽器自動解壓縮，前端無需額外處理
- UAV 圖層佔最大比例（4,744 筆、~25 MB），其他圖層很小

---

### 2. `POST /api/zones/check`

檢查指定座標是否落在禁限航區內。

**Request Body：**

```json
{
  "lng": 121.5654,
  "lat": 25.0330
}
```

**Response（200）：**

```json
{
  "in_zone": true,
  "zones": [
    {
      "id": 5,
      "layer": "UAV",
      "name": "松山機場"
    }
  ]
}
```

**實作要點：**
- 使用 Pydantic `BaseModel`（`CheckPointRequest`）接收 JSON body，不可用裸 `float` 參數（否則 FastAPI 會當成 query parameter）
- 使用 `func.ST_Contains(NoFlyZone.geometry, func.ST_GeomFromText(f'POINT({lng} {lat})', 4326))` 進行空間查詢
- 注意 WKT POINT 格式為 `POINT(lng lat)`（經度在前）
- 回傳所有包含該點的禁限航區

---

### 3. `POST /api/zones/refresh`

手動觸發資料同步。

**Request Body：** 無

**Response（200）：**

```json
{
  "message": "同步完成",
  "count": 156
}
```

**實作要點：**
- 呼叫 `refresh_zones()` 執行全量替換
- 回傳寫入筆數
- 注意 `refresh_zones()` 內部呼叫的 `fetch_layer()` 是同步 HTTP 呼叫，會在 fetch 階段阻塞 event loop

## 驗證

啟動 server 後：

```bash
# 查詢所有 zones
curl http://localhost:8000/api/zones

# 依圖層篩選
curl http://localhost:8000/api/zones?layer=UAV

# 座標檢查
curl -X POST http://localhost:8000/api/zones/check \
  -H "Content-Type: application/json" \
  -d '{"lng": 121.5654, "lat": 25.0330}'

# 手動刷新
curl -X POST http://localhost:8000/api/zones/refresh
```
