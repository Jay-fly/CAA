"""禁航區 API 路由。

提供兩個 endpoint：
- GET  /zones       — 查詢禁航區（可選 layer 篩選）
- POST /zones/check — 座標點位是否落在禁航區內
"""

import json

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from caa_nfz.database import async_session
from caa_nfz.models import NoFlyZone

router = APIRouter()


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
            # ST_AsGeoJSON() 與 properties 欄位回傳的是 JSON 字串，需解析為 dict
            "properties": json.loads(row.properties) if row.properties else None,
            "geometry": json.loads(row.geometry),
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
    return {"count": len(zones), "zones": zones}


@router.post("/zones/check")
async def check_point(body: CheckPointRequest):
    """判斷指定經緯度是否落在禁航區內，回傳命中的禁航區 ID 清單。"""
    point = func.ST_GeomFromText(f"POINT({body.lng} {body.lat})", 4326)
    stmt = select(NoFlyZone.id).where(func.ST_Contains(NoFlyZone.geometry, point))

    async with async_session() as session:
        rows = (await session.execute(stmt)).all()

    zone_ids = [row.id for row in rows]
    return {"in_zone": len(zone_ids) > 0, "zone_ids": zone_ids}
