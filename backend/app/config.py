from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]

_PLACEHOLDER_KEYS = {"", "your_openai_api_key_here"}


class Settings(BaseSettings):
    project_name: str = "DocLens API"

    # --- Secrets / model providers ---
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""

    # --- Model selection (no hardcoded model names in code) ---
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o-mini"

    # --- Ingestion ---
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # --- Retrieval ---
    hybrid_dense_weight: float = 0.5
    hybrid_sparse_weight: float = 0.5
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # --- Paths / CORS ---
    data_dir: str = str(PROJECT_ROOT / "data")
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def openai_configured(self) -> bool:
        """True when a real (non-placeholder) OpenAI key is present."""
        return self.openai_api_key not in _PLACEHOLDER_KEYS


settings = Settings()
