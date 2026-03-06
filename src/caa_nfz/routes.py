"""禁航區 API 路由。

提供三個 endpoint：
- GET  /zones         — 查詢禁航區（可選 layer 篩選）
- POST /zones/check   — 座標點位是否落在禁航區內
- POST /zones/refresh — 手動觸發資料同步（需 Bearer Token）
"""

import asyncio
import hmac
import logging

import orjson
from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select

from caa_nfz.database import async_session
from caa_nfz.models import NoFlyZone
from caa_nfz.services import refresh_zones
from caa_nfz.settings import settings

router = APIRouter()
log = logging.getLogger(__name__)
_refresh_lock = asyncio.Lock()


class CheckPointRequest(BaseModel):
    lng: float
    lat: float


@router.get("/zones")
async def get_zones(layer: str | None = Query(None)):
    """查詢禁航區資料。可透過 layer 參數篩選特定圖層，不帶參數則回傳全部。"""
    stmt = select(
        NoFlyZone.id,
        NoFlyZone.layer,
        NoFlyZone.name,
        NoFlyZone.properties,
        func.ST_AsGeoJSON(NoFlyZone.geometry).label("geometry"),
        NoFlyZone.created_at,
    )
    if layer is not None:
        stmt = stmt.where(NoFlyZone.layer == layer)

    async with async_session() as session:
        rows = (await session.execute(stmt)).all()

    zones = [
        {
            "id": row.id,
            "layer": row.layer,
            "name": row.name,
            "properties": orjson.Fragment(row.properties) if row.properties else None,
            "geometry": orjson.Fragment(row.geometry),
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
    payload = orjson.dumps({"count": len(zones), "zones": zones})

    return Response(content=payload, media_type="application/json")


@router.post("/zones/check")
async def check_point(body: CheckPointRequest):
    """判斷指定經緯度是否落在禁航區內，回傳命中的禁航區 ID 清單。"""
    point = func.ST_GeomFromText(f"POINT({body.lng} {body.lat})", 4326)
    stmt = select(NoFlyZone.id).where(func.ST_Contains(NoFlyZone.geometry, point))

    async with async_session() as session:
        rows = (await session.execute(stmt)).all()

    zone_ids = [row.id for row in rows]
    return {"in_zone": len(zone_ids) > 0, "zone_ids": zone_ids}


async def _run_refresh() -> None:
    """背景執行 refresh_zones()。"""
    async with _refresh_lock:
        try:
            count = await refresh_zones()
            log.info("背景同步完成，共 %d 筆", count)
        except Exception:
            log.exception("背景同步失敗")


@router.post("/zones/refresh", include_in_schema=False)
async def post_refresh_zones(
    authorization: str = Header(default=""),
):
    """手動觸發禁航區資料同步（需 Bearer Token）。"""
    expected = f"Bearer {settings.admin_token}"
    if not settings.admin_token or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if _refresh_lock.locked():
        raise HTTPException(status_code=409, detail="同步正在執行中")

    asyncio.create_task(_run_refresh())
    return {"message": "同步已排入背景執行"}
