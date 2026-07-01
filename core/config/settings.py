"""TourSwarm global settings.

Configuration is loaded from environment variables and an optional ``.env`` file.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded via pydantic-settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    amap_api_key: str = Field(default="", description="Amap Web Service API key")
    amap_base_url: str = "https://restapi.amap.com/v3"

    qweather_api_key: str = Field(default="", description="QWeather API key")
    qweather_base_url: str = "https://api.qweather.com/v7"
    qweather_geo_url: str = "https://geoapi.qweather.com/v2"

    caiyun_api_key: str = ""

    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_light_model: str = "gpt-4o-mini"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "tourswarm"
    postgres_password: str = "tourswarm_dev"
    postgres_db: str = "tourswarm"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_secret_key: str = "change-me-in-production"

    langsmith_api_key: str = ""
    langsmith_project: str = "tourswarm"

    mem0_vector_store: str = "qdrant"
    mem0_embedder_model: str = "BAAI/bge-large-zh-v1.5"

    @property
    def postgres_dsn(self) -> str:
        """Return the async PostgreSQL DSN."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Return the Redis connection URL."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    """Return cached global settings."""
    return Settings()
