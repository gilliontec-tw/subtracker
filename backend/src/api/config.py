from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    redis_url: str = ""

    jwt_access_secret_key: str = ""
    jwt_refresh_secret_key: str = ""
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    cors_origins: list[str] = []

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_sender_name: str = "SubTrack"

    settings_encryption_key: str = ""
    notification_cron_hour: int = 8
    notification_cron_minute: int = 0

    app_env: str = "production"
    app_url: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
