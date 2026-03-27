from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    project_name: str = "DocLens API"
    openai_api_key: str
    chunk_size: int = 1000
    chunk_overlap: int = 200
    hybrid_dense_weight: float = 0.5
    hybrid_sparse_weight: float = 0.5
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
