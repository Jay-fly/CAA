# Scope 3: 資料庫層

## 目標

建立 SQLAlchemy model 與 async database engine，定義 `no_fly_zones` 資料表 schema。

## 新增檔案

### `src/caa_nfz/models.py`

```python
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class NoFlyZone(Base):
    __tablename__ = "no_fly_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    layer: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    properties: Mapped[str | None] = mapped_column(Text)  # JSON string of original attributes
    geometry = mapped_column(Geometry(srid=4326), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

**欄位說明：**

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | `INTEGER PK` | 自動遞增主鍵 |
| `layer` | `VARCHAR(50)` | 圖層名稱（UAV, National_Park 等），建立 index |
| `name` | `VARCHAR(255)` | 區域名稱（從 attributes 提取） |
| `properties` | `TEXT` | 原始 attributes 的 JSON 字串 |
| `geometry` | `Geometry(SRID=4326)` | PostGIS 空間欄位 |
| `created_at` | `TIMESTAMPTZ` | 資料寫入時間 |

### `src/caa_nfz/database.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from caa_nfz.models import Base
from caa_nfz.settings import settings

engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """建立所有資料表（含 PostGIS extension）。"""
    async with engine.begin() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        await conn.run_sync(Base.metadata.create_all)
```

## PostGIS Spatial Index

GeoAlchemy2 的 `Geometry` 欄位在 `create_all` 時會自動建立 GiST spatial index，無需手動建立。

這使得 `ST_Contains`、`ST_Intersects` 等空間查詢能高效執行。

## 資料庫準備

開發環境需先建立 PostgreSQL 資料庫與啟用 PostGIS：

```sql
CREATE DATABASE caa_nfz;
\c caa_nfz
CREATE EXTENSION IF NOT EXISTS postgis;
```

或使用 Docker：

```bash
docker run -d \
  --name caa-nfz-db \
  -e POSTGRES_DB=caa_nfz \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgis/postgis:17-3.5
```

## 驗證

啟動應用後，連線到資料庫確認資料表已建立：

```sql
\dt no_fly_zones
\di  -- 確認 spatial index 存在
```
