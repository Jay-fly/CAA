# CAA 禁限航區後端服務

## 專案目標

將現有的 CAA 無人機禁飛區爬蟲（crawler-only）升級為完整的後端服務，提供：

1. **資料持久化** — 將爬取的禁限航區資料存入 PostgreSQL/PostGIS
2. **REST API** — 提供查詢、座標檢查、手動刷新等 endpoints
3. **定時同步** — 透過排程自動更新資料

## 技術選型

| 元件 | 技術 | 說明 |
|------|------|------|
| Web 框架 | FastAPI | 非同步、自動 OpenAPI 文件 |
| 資料庫 | PostgreSQL + PostGIS | 空間資料原生支援 |
| ORM | SQLAlchemy 2.0 + GeoAlchemy2 | async engine、空間欄位 |
| 設定管理 | pydantic-settings | 環境變數驗證與型別轉換 |
| 排程 | APScheduler 3.x | 簡單的 interval job |
| HTTP 客戶端 | httpx | 既有依賴，維持不變 |

## 最終檔案結構

```
src/caa_nfz/
├── app.py          # FastAPI 應用程式入口、lifespan
├── config.py       # 爬蟲圖層設定（既有）
├── converter.py    # ArcGIS → GeoJSON 轉換（既有）
├── crawler.py      # 圖層爬取邏輯（既有，移除 main entry point）
├── database.py     # async engine、session factory、init_db
├── models.py       # SQLAlchemy model（no_fly_zones 資料表）
├── routes.py       # API 路由（/api/zones, /api/zones/check, /api/zones/refresh）
├── scheduler.py    # APScheduler interval job
├── services.py     # refresh_zones() 業務邏輯
└── settings.py     # pydantic-settings 環境變數管理
```

## Scope 列表與依賴關係

| Scope | 文件 | 說明 | 依賴 |
|-------|------|------|------|
| 1 | [scope-1-dependencies.md](scope-1-dependencies.md) | 安裝依賴 | — |
| 2 | [scope-2-settings.md](scope-2-settings.md) | 應用程式設定 | Scope 1 |
| 3 | [scope-3-database.md](scope-3-database.md) | 資料庫層 | Scope 2 |
| 4 | [scope-4-services.md](scope-4-services.md) | 資料同步服務 | Scope 3 |
| 5 | [scope-5-api.md](scope-5-api.md) | API 路由 | Scope 4 |
| 6 | [scope-6-scheduler.md](scope-6-scheduler.md) | 定時排程 | Scope 4 |
| 7 | [scope-7-app-entry.md](scope-7-app-entry.md) | 應用程式入口 | Scope 5, 6 |

```
Scope 1 → Scope 2 → Scope 3 → Scope 4 → Scope 5 ─┐
                                         └→ Scope 6 ─┼→ Scope 7
```
