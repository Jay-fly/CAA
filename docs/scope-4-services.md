# Scope 4: 資料同步服務

## 目標

建立 `services.py` 封裝 `refresh_zones()` 業務邏輯，負責爬取所有圖層並寫入資料庫。同時修改 `crawler.py` 移除 `main()` entry point。

## 新增檔案

### `src/caa_nfz/services.py`

```python
import json
import logging

from sqlalchemy import delete

from caa_nfz.converter import _arcgis_geometry_to_geojson
from caa_nfz.crawler import fetch_all_layers
from caa_nfz.database import async_session
from caa_nfz.models import NoFlyZone

log = logging.getLogger(__name__)


async def refresh_zones() -> int:
    """爬取所有圖層，全量替換資料庫中的資料。回傳寫入筆數。"""
    all_data = fetch_all_layers()

    rows: list[NoFlyZone] = []
    for layer_name, features in all_data.items():
        for f in features:
            attrs = f.get("attributes", {})
            geojson_geom = _arcgis_geometry_to_geojson(f.get("geometry", {}))
            if geojson_geom is None:
                continue

            rows.append(
                NoFlyZone(
                    layer=layer_name,
                    name=attrs.get("NAME") or attrs.get("name"),
                    properties=json.dumps(attrs, ensure_ascii=False),
                    geometry=f"SRID=4326;{json.dumps(geojson_geom)}",
                )
            )

    async with async_session() as session:
        async with session.begin():
            await session.execute(delete(NoFlyZone))
            session.add_all(rows)

    log.info("refresh_zones 完成: 寫入 %d 筆", len(rows))
    return len(rows)
```

## 同步策略：全量替換（DELETE + INSERT）

採用 **全量替換** 而非增量更新：

1. **DELETE** — 清空 `no_fly_zones` 所有資料
2. **INSERT** — 寫入本次爬取的所有資料

兩步驟在同一個 transaction 內，確保原子性。若 INSERT 失敗會 rollback，資料不會遺失。

**選擇此策略的原因：**
- CAA 來源資料無穩定的 unique ID，難以做 diff/merge
- 資料量不大（約數百筆），全量替換成本低
- 邏輯簡單，不易產生 stale data

## 修改既有檔案

### `src/caa_nfz/crawler.py` — 移除 main entry point

刪除 `main()` 函式與 `if __name__ == "__main__":` 區塊。`fetch_layer()` 與 `fetch_all_layers()` 保留不變。

```python
# 移除以下內容：
# def main(): ...
# if __name__ == "__main__": ...
```

### `pyproject.toml` — 移除 scripts entry

```diff
-[project.scripts]
-caa-nfz = "caa_nfz.crawler:main"
```

> entry point 會在 Scope 7 改為指向 FastAPI app。

## 驗證

```python
import asyncio
from caa_nfz.services import refresh_zones

count = asyncio.run(refresh_zones())
print(f"寫入 {count} 筆")
```
