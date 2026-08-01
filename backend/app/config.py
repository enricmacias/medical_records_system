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
    ollama_timeout_seconds: float = 90.0
    # async: return upload immediately and process in background (avoids gateway timeouts)
    # sync: wait for extraction+LLM before responding (useful for tests)
    processing_mode: str = "async"
    # When true, skip demographics LLM if heuristics already found pet.name
    llm_skip_demographics_when_hinted: bool = True
    # heuristic: no LLM clinical call (fastest)
    # hybrid: heuristics first; LLM only when clinical hints are weak (default)
    # llm: always call LLM for clinical narrative (slowest, may timeout on 7B)
    llm_clinical_mode: str = "hybrid"
    ollama_num_predict: int = 384
    ollama_num_ctx: int = 4096

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
