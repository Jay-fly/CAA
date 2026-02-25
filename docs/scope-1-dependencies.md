# Scope 1: 安裝依賴

## 目標

安裝後端服務所需的所有 Python 套件。

## 套件列表

| 套件 | 用途 |
|------|------|
| `fastapi` | Web 框架，自動生成 OpenAPI 文件 |
| `uvicorn[standard]` | ASGI server，執行 FastAPI 應用 |
| `sqlalchemy[asyncio]` | ORM，async engine 支援 |
| `asyncpg` | PostgreSQL async driver（搭配 SQLAlchemy） |
| `geoalchemy2` | SQLAlchemy 的 PostGIS 空間欄位支援 |
| `pydantic-settings` | 環境變數管理，型別驗證 |
| `apscheduler` | 定時排程，interval job |

> `httpx` 已存在於 dependencies 中，無需額外安裝。

## 實作步驟

### 1. 使用 PDM 安裝依賴

```bash
pdm add fastapi "uvicorn[standard]" "sqlalchemy[asyncio]" asyncpg geoalchemy2 pydantic-settings apscheduler
```

### 2. 驗證

```bash
pdm list --fields name,version
```

確認上述套件皆出現在輸出中。

### 3. 預期的 pyproject.toml 變更

`[project] dependencies` 區塊應包含：

```toml
dependencies = [
    "httpx>=0.28",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "geoalchemy2>=0.17",
    "pydantic-settings>=2.7",
    "apscheduler>=3.10,<4",
]
```

> 版本號以安裝時的最新穩定版為準，上述為最低建議版本。
