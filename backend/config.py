"""Centralised configuration. Loads from backend/.env (gitignored)."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ----- LLM -----
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    nemotron_reasoner: str = "nvidia/llama-3.3-nemotron-super-49b-v1"
    nemotron_fast: str = "nvidia/nemotron-nano-9b-v2"
    embedding_model: str = "nvidia/nv-embedqa-e5-v5"

    # ----- External APIs -----
    tavily_api_key: str = ""
    openweather_api_key: str = ""
    usda_api_key: str = ""

    # ----- Paths (resolved relative to backend/) -----
    chroma_dir: Path = Path(__file__).parent / "data" / "chroma"
    sqlite_path: Path = Path(__file__).parent / "data" / "tulparai.db"

    # ----- Pipeline tuning -----
    confidence_threshold: float = 0.35
    top_k_retrieval: int = 15
    top_k_rerank: int = 5
    chunk_size: int = 600
    chunk_overlap: int = 120

    # ----- Server -----
    port: int = 8000
    cors_origins: str = "http://localhost:3000"


settings = Settings()
