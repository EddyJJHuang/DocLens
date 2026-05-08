from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    project_name: str = "DocLens API"
    openai_api_key: str = ""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    hybrid_dense_weight: float = 0.5
    hybrid_sparse_weight: float = 0.5
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    data_dir: str = str(PROJECT_ROOT / "data")
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
