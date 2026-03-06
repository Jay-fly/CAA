# Scope 13: 統一 properties 欄位格式

## 目標

統一 5 個 layer 的 `properties` JSON 為一組固定 12 欄位的英文 schema，所有 layer 都輸出相同欄位集合，沒有值填 `null`。

## 問題背景

資料庫中 5 個 layer 的 `properties` 來自不同 ArcGIS endpoint，各有不同的中/英文 key 和不同數量的欄位：

- `Commercial_Port`：15 個 key（中英混用）
- `Kinmen_Matsu`：3 個 key
- `National_Park`：5 個 key
- `UAV` / `Temporary_Area`：26 個 key（含多個 null audit 欄位）

前端需要針對每個 layer 寫不同的解析邏輯，維護困難。

## 統一 Schema（12 欄位）

```json
{
  "name": "商港-安平港17禁止飛行區域",
  "description": "禁止飛行區域",
  "condition": "禁止",
  "zone_color": "紅區",
  "zone_category": "縣市政府限制使用範圍",
  "authority": "臺灣港務股份有限公司",
  "consultation_authority": null,
  "contact": "承辦窗口：...",
  "local_government": "交通部航港局",
  "penalty": null,
  "regulation_url": null,
  "valid_from": "2026-01-28",
  "valid_to": "2910-12-31"
}
```

各欄位的 layer 來源對照：

| 欄位 | Commercial_Port | Kinmen_Matsu | National_Park | UAV / Temporary_Area |
|------|----------------|-------------|--------------|---------------------|
| name | `名稱` 或 `name` | — | `name_full` | `空域名稱` |
| description | `說明` | `說明` | — | `空域說明` |
| condition | `條件` | — | — | `條件` |
| zone_color | — | — | — | `空域顏色` |
| zone_category | — | — | — | `空域類別名稱` |
| authority | `管理_及會商_機關` | — | — | `主管機關名稱` |
| consultation_authority | — | — | — | `會商機關名稱` |
| contact | `管理_及會商_機關聯絡方式` | — | — | `聯絡方式` |
| local_government | `所在地_應公告之地方政府_` | — | — | — |
| penalty | — | — | — | `罰則` |
| regulation_url | — | — | `相關規` | — |
| valid_from | `有效日期起` (epoch ms) | — | — | `有效日期起` (民國年) |
| valid_to | `有效日期迄` (epoch ms) | — | — | `有效日期迄` (民國年) |

丟棄的原始欄位：`objectid`, `SHAPE__Area`, `SHAPE__Length`, `半徑`, `項次`, `座標類型`, `restriction_level`, `空域類別`, `空域類型`, `主管機關`(代碼), `會商機關`(代碼), `countyid`, `created_user/date`, `last_edited_user/date`, `二級機關`, `三級機關`。

## 日期格式統一

| 來源格式 | Layer | 轉換規則 | 範例 |
|---------|-------|---------|------|
| epoch milliseconds | Commercial_Port | `datetime.fromtimestamp(v/1000).strftime('%Y-%m-%d')` | `1769904000000` → `"2026-01-28"` |
| 民國年字串 `YYY/M/D` | UAV, Temporary_Area | 年份 +1911，補零 | `"115/3/16"` → `"2026-03-16"` |

## 新增檔案

### `src/caa_nfz/normalizer.py`

新增模組，包含：

1. per-layer 的 `原始 key → unified key` 映射 dict
2. `normalize_properties(layer: str, attrs: dict) -> dict` 函數：
   - 初始化 12 個 key 全為 `null` 的 dict
   - 根據 layer 的映射表，從 `attrs` 取值填入
   - 對 `valid_from` / `valid_to` 做日期格式轉換

## 修改既有檔案

### `src/caa_nfz/services.py`

第 44 行，將原始 attrs 改為經過 normalize 的版本：

```python
# Before
properties=json.dumps(attrs, ensure_ascii=False),

# After
properties=json.dumps(normalize_properties(layer_name, attrs), ensure_ascii=False),
```

新增 import：

```python
from caa_nfz.normalizer import normalize_properties
```

### 不需要修改的檔案

- `routes.py` — 仍用 `orjson.Fragment(row.properties)` 直接輸出
- `models.py` — `properties` 仍為 `Text` 型別
- `config.py` — 不動

## 驗證步驟

### 1. Lint 檢查

```bash
pdm run ruff check src/caa_nfz/normalizer.py src/caa_nfz/services.py
```

### 2. 手動觸發 refresh

```bash
curl -X POST http://localhost:8000/api/zones/refresh \
  -H "Authorization: Bearer <token>"
```

### 3. 確認 properties 格式統一

```sql
-- 各 layer 的 properties key 應完全相同（12 個）
SELECT layer,
       (SELECT array_agg(k ORDER BY k) FROM json_object_keys(properties::json) AS k) AS keys
FROM no_fly_zones
GROUP BY layer, keys;
```

### 4. 確認 API 回傳

```bash
curl http://localhost:8000/api/zones?layer=Commercial_Port | python -m json.tool
```

預期：每筆 zone 的 `properties` 都有完整 12 個 key，日期格式為 ISO date。
