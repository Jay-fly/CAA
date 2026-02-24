def _arcgis_geometry_to_geojson(geometry: dict) -> dict | None:
    """將 ArcGIS geometry（rings/paths）轉成 GeoJSON geometry。"""
    rings = geometry.get("rings")
    if rings:
        return {"type": "Polygon", "coordinates": rings}
    paths = geometry.get("paths")
    if paths:
        if len(paths) == 1:
            return {"type": "LineString", "coordinates": paths[0]}
        return {"type": "MultiLineString", "coordinates": paths}
    return None


def to_geojson(layer_name: str, features: list[dict]) -> dict:
    """將 ArcGIS features 轉成標準 GeoJSON FeatureCollection。"""
    geojson_features = []
    for f in features:
        geom = _arcgis_geometry_to_geojson(f.get("geometry", {}))
        geojson_features.append(
            {
                "type": "Feature",
                "properties": f.get("attributes", {}),
                "geometry": geom,
            }
        )
    return {
        "type": "FeatureCollection",
        "features": geojson_features,
    }
