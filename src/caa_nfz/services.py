import json
import logging

from sqlalchemy import delete

from caa_nfz.config import LAYERS
from caa_nfz.converter import _arcgis_geometry_to_geojson
from caa_nfz.crawler import fetch_layer
from caa_nfz.database import async_session
from caa_nfz.models import NoFlyZone

log = logging.getLogger(__name__)

BATCH_SIZE = 500


async def refresh_zones() -> int:
    """爬取所有圖層，全量替換資料庫中的資料。回傳寫入筆數。"""
    total = 0

    async with async_session() as session, session.begin():
        await session.execute(delete(NoFlyZone))

        batch: list[NoFlyZone] = []
        for layer_name, cfg in LAYERS.items():
            features = fetch_layer(layer_name, cfg["endpoint"])
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
