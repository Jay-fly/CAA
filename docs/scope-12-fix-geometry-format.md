# Scope 12: 修復 geometry 寫入格式錯誤

## 目標

修復 `services.py` 中 geometry 欄位寫入格式錯誤，改用 Shapely + GeoAlchemy2 正確轉換 GeoJSON 為 WKBElement。

## 問題背景

`services.py:43` 把 GeoJSON dict 用 `json.dumps` 序列化後接在 `SRID=4326;` 後面：

```python
geometry=f"SRID=4326;{json.dumps(geojson_geom)}"
```

產出 `SRID=4326;{"type": "Polygon", ...}`，但 GeoAlchemy2 的 `Geometry` 欄位預設用 `ST_GeomFromEWKT` 解析，EWKT 格式應為 `SRID=4326;POLYGON((...))` 而非 GeoJSON。

PostGIS 錯誤：

```
parse error - invalid geometry HINT: "SRID=4326;{"" <-- parse error at position 12
```

## 修改既有檔案

### `src/caa_nfz/services.py`

用 `geoalchemy2.shape.from_shape` + `shapely.geometry.shape` 將 GeoJSON dict 轉為 `WKBElement`：

- `shapely.geometry.shape(geojson_geom)` — GeoJSON dict → Shapely geometry
- `geoalchemy2.shape.from_shape(shapely_geom, srid=4326)` — Shapely geometry → `WKBElement`

修改範圍：

1. 新增 import：

```python
from geoalchemy2.shape import from_shape
from shapely.geometry import shape
```

2. 第 43 行改為：

```python
geometry=from_shape(shape(geojson_geom), srid=4326),
```

3. 移除不再需要的 `import json`（檢查是否仍有其他用途，若第 42 行 `json.dumps(attrs)` 仍在使用則保留）。

## 驗證步驟

### 1. Lint 檢查

```bash
pdm run ruff check src/caa_nfz/services.py
```

### 2. 手動觸發 refresh

```bash
curl -X POST http://localhost:8000/api/zones/refresh \
  -H "Authorization: Bearer <token>"
```

預期：不再出現 `parse error - invalid geometry`，資料正常寫入。
