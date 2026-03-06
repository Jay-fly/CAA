"""Normalize per-layer ArcGIS attributes into a unified 12-field schema."""

from __future__ import annotations

from datetime import UTC, datetime

UNIFIED_KEYS = [
    "name",
    "description",
    "condition",
    "zone_color",
    "zone_category",
    "authority",
    "consultation_authority",
    "contact",
    "local_government",
    "penalty",
    "regulation_url",
    "valid_from",
    "valid_to",
]

# Per-layer mapping: {original_key: unified_key}
_COMMERCIAL_PORT_MAP = {
    "名稱": "name",
    "說明": "description",
    "條件": "condition",
    "管理_及會商_機關": "authority",
    "管理_及會商_機關聯絡方式": "contact",
    "所在地_應公告之地方政府_": "local_government",
    "有效日期起": "valid_from",
    "有效日期迄": "valid_to",
}

_KINMEN_MATSU_MAP = {
    "說明": "description",
}

_NATIONAL_PARK_MAP = {
    "name_full": "name",
    "相關規": "regulation_url",
}

_UAV_MAP = {
    "空域名稱": "name",
    "空域說明": "description",
    "條件": "condition",
    "空域顏色": "zone_color",
    "空域類別名稱": "zone_category",
    "主管機關名稱": "authority",
    "會商機關名稱": "consultation_authority",
    "聯絡方式": "contact",
    "罰則": "penalty",
    "有效日期起": "valid_from",
    "有效日期迄": "valid_to",
}

_LAYER_MAPS: dict[str, dict[str, str]] = {
    "Commercial_Port": _COMMERCIAL_PORT_MAP,
    "Kinmen_Matsu": _KINMEN_MATSU_MAP,
    "National_Park": _NATIONAL_PARK_MAP,
    "UAV": _UAV_MAP,
    "Temporary_Area": _UAV_MAP,
}

# Layers whose date fields are epoch milliseconds.
_EPOCH_MS_LAYERS = {"Commercial_Port"}
# Layers whose date fields are ROC date strings (YYY/M/D).
_ROC_DATE_LAYERS = {"UAV", "Temporary_Area"}


def _epoch_ms_to_date(value: object) -> str | None:
    """Convert epoch milliseconds to ISO date string."""
    if value is None:
        return None
    try:
        ts = int(value) / 1000
        return datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OSError):
        return None


def _roc_date_to_date(value: object) -> str | None:
    """Convert ROC date string (YYY/M/D) to ISO date string."""
    if not value or not isinstance(value, str):
        return None
    parts = value.split("/")
    if len(parts) != 3:
        return None
    try:
        year = int(parts[0]) + 1911
        month = int(parts[1])
        day = int(parts[2])
        return f"{year:04d}-{month:02d}-{day:02d}"
    except (ValueError, TypeError):
        return None


def normalize_properties(layer: str, attrs: dict) -> dict:
    """Transform raw ArcGIS attributes into the unified 12-field schema."""
    mapping = _LAYER_MAPS.get(layer, {})
    result: dict[str, object] = {k: None for k in UNIFIED_KEYS}

    for src_key, dst_key in mapping.items():
        if src_key in attrs:
            result[dst_key] = attrs[src_key]

    # Date conversion
    if layer in _EPOCH_MS_LAYERS:
        result["valid_from"] = _epoch_ms_to_date(result["valid_from"])
        result["valid_to"] = _epoch_ms_to_date(result["valid_to"])
    elif layer in _ROC_DATE_LAYERS:
        result["valid_from"] = _roc_date_to_date(result["valid_from"])
        result["valid_to"] = _roc_date_to_date(result["valid_to"])

    return result
