from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ASSETFORGE_",
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    default_locale: str = "zh-CN"
    supported_locales: str = "zh-CN,en"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/assetforge.db"
    model_provider: str = "mock"
    model_api_base_url: str = ""
    model_api_key: str = ""
    model_name: str = ""
    tripo_api_base_url: str = "https://api.tripo3d.ai/v2/openapi"
    tripo_api_key: str = ""
    tripo_model_version: str = "P1-20260311"
    image_model_name: str = "seedream-image-v5.0-pro"
    model_timeout_seconds: int = 900
    image_model_timeout_seconds: int = 180
    image_model_max_retries: int = 0
    model_max_retries: int = 2
    asset_storage_root: Path = Path("./data")
    public_base_url: str = "http://localhost:8010"
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "https://assetforge-alpha.mornoxborn89.chatgpt.site"
    )
    max_model_file_mb: int = 500
    max_reference_image_mb: int = 20
    max_reference_image_dimension: int = 8_192
    max_concept_image_mb: int = 20
    internal_cost_tracking: bool = True

    @property
    def locales(self) -> list[str]:
        return [item.strip() for item in self.supported_locales.split(",") if item.strip()]

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [item.strip().rstrip("/") for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
