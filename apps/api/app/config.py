from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "Notebook"
    log_level: str = "INFO"
    database_url: str = Field(
        default="postgresql+asyncpg://notebook:notebook_dev_password@127.0.0.1:5432/notebook"
    )
    redis_url: str = "redis://127.0.0.1:6379/0"
    storage_root: str = "./data"
    max_attachment_bytes: int = 10 * 1024 * 1024
    allowed_attachment_types: str = (
        "image/png,image/jpeg,image/gif,image/webp,text/plain,text/markdown,application/pdf"
    )
    ai_organizer_settings_path: str | None = None
    organizer_provider: str = "local"
    minimax_api_key: str | None = None
    minimax_base_url: str = "https://api.minimaxi.com/anthropic"
    minimax_model: str = "MiniMax-M3"
    minimax_max_tokens: int = 8192
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_max_tokens: int = 8192
    deepseek_timeout_seconds: float = 60.0
    deepseek_thinking_enabled: bool = False
    embedding_provider: str = "local"
    embedding_model: str = "local-hash-embedding-v1"
    embedding_dimensions: int = 1536
    embedding_base_url: str = "https://api.minimaxi.com/v1"
    embedding_api_key: str | None = None
    embedding_group_id: str | None = None
    embedding_timeout_seconds: float = 30.0
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_attachment_type_set(self) -> set[str]:
        return {
            media_type.strip()
            for media_type in self.allowed_attachment_types.split(",")
            if media_type.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
