"""Application settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Veterinary Medical Records"
    database_url: str = "sqlite:///./data/app.db"
    upload_dir: Path = Path("./data/uploads")
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    llm_provider: str = "ollama"  # ollama | fake
    max_upload_bytes: int = 10 * 1024 * 1024
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    ollama_timeout_seconds: float = 120.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
