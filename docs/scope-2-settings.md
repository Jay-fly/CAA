# Scope 2: 應用程式設定

## 目標

建立 `settings.py`，使用 pydantic-settings 管理環境變數，統一所有可配置項目。

## 新增檔案

### `src/caa_nfz/settings.py`

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "CAA_"}

    # 資料庫
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/caa_nfz"

    # 排程
    refresh_interval_minutes: int = 60

    # API
    api_prefix: str = "/api"


settings = Settings()
```

## 環境變數列表

| 環境變數 | 型別 | 預設值 | 說明 |
|----------|------|--------|------|
| `CAA_DATABASE_URL` | `str` | `postgresql+asyncpg://postgres:postgres@localhost:5432/caa_nfz` | 資料庫連線字串（async driver） |
| `CAA_REFRESH_INTERVAL_MINUTES` | `int` | `60` | 定時同步間隔（分鐘） |
| `CAA_API_PREFIX` | `str` | `/api` | API 路由前綴 |

## 說明

- 所有環境變數以 `CAA_` 為前綴，避免與其他應用衝突
- `database_url` 預設使用 `asyncpg` driver，對應 SQLAlchemy async engine
- 透過 `settings = Settings()` 匯出單例，其他模組直接 `from caa_nfz.settings import settings`

## 驗證

```python
from caa_nfz.settings import settings
print(settings.database_url)
print(settings.refresh_interval_minutes)
```
