"""Centralised configuration. Loads from backend/.env (gitignored).

Relative paths in `.env` (e.g. `CHROMA_DIR=./data/chroma`) are resolved against
the `backend/` directory — NOT the process CWD — so the same `.env` works
whether you launch from project root or from `backend/`.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

# `backend/` directory — the anchor for relative paths
BACKEND_DIR = Path(__file__).parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ----- LLM -----
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    nemotron_reasoner: str = "nvidia/nemotron-3-super-120b-a12b"
    nemotron_fast: str = "nvidia/nvidia-nemotron-nano-9b-v2"
    embedding_model: str = "nvidia/nv-embedqa-e5-v5"

    # ----- External APIs -----
    tavily_api_key: str = ""
    openweather_api_key: str = ""
    usda_api_key: str = ""

    # ----- Paths (relative paths resolved against backend/) -----
    chroma_dir: Path = BACKEND_DIR / "data" / "chroma"
    sqlite_path: Path = BACKEND_DIR / "data" / "tulparai.db"

    # ----- Pipeline tuning -----
    confidence_threshold: float = 0.35
    top_k_retrieval: int = 15
    top_k_rerank: int = 5
    chunk_size: int = 600
    chunk_overlap: int = 120

    # ----- Server -----
    port: int = 8000
    cors_origins: str = "http://localhost:3000"

    @field_validator("chroma_dir", "sqlite_path", mode="before")
    @classmethod
    def _resolve_path(cls, v):
        """Anchor relative paths to backend/ so they don't depend on cwd."""
        if v is None:
            return v
        p = Path(v) if not isinstance(v, Path) else v
        if not p.is_absolute():
            p = (BACKEND_DIR / p).resolve()
        return p


settings = Settings()
