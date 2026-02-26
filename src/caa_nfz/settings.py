from pydantic import computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 資料庫
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "caa_nfz"

    # 排程
    refresh_interval_minutes: int = 60

    @computed_field
    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
