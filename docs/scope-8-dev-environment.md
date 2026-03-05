# Scope 8: Docker 開發環境

## 目標

提供 Docker Compose 設定，一鍵啟動 PostgreSQL + PostGIS 開發資料庫，並建立 `.env.example` 列出所有環境變數。

## 新建檔案

### `docker-compose.yml`

```yaml
services:
  db:
    image: postgis/postgis:17-3.5
    platform: linux/amd64
    environment:
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}
      POSTGRES_DB: ${DB_NAME:-caa_nfz}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

重點：
- 映像版本 `postgis/postgis:17-3.5` 與 Scope 3 文件中的範例一致
- 環境變數對齊 `settings.py` 預設值（`postgres` / `postgres` / `caa_nfz`）
- Named volume `pgdata` 確保容器重建後資料不遺失

### `.env.example`

```dotenv
# 資料庫
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=caa_nfz

# 排程
REFRESH_INTERVAL_MINUTES=60

# API
API_PREFIX=/api
ADMIN_TOKEN=my-secret-token
```

## 驗證步驟

### 1. 啟動資料庫

```bash
docker compose up -d
```

### 2. 確認 PostGIS 可用

```bash
docker compose exec db psql -U postgres -d caa_nfz -c "SELECT PostGIS_Version();"
```

預期輸出包含版本號，例如 `3.5 ...`。

### 3. 停止資料庫

```bash
docker compose down
```

> 加上 `-v` flag 可同時刪除 volume：`docker compose down -v`
