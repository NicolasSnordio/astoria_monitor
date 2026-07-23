from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.version import __version__


class Settings(BaseSettings):
    app_name: str = "Astoria Monitor"
    app_version: str = __version__
    database_url: str = "sqlite:///./data/astoria_monitor.db"
    agent_shared_token: str = ""
    app_secret_key: str = "astoria-monitor-dev-secret"
    admin_username: str = "admin"
    admin_password: str = "admin"
    admin_display_name: str = "TI Astoria"
    offline_after_minutes: int = 10
    disk_low_threshold_gb: float = 15

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
