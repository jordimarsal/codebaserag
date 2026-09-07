from pydantic_settings import BaseSettings, SettingsConfigDict


# region Settings
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CODERAG_", extra="ignore")

    database_dsn: str = "postgresql://localhost:5432/codebaserag"
    embedder_url: str = "http://localhost:11434"
    embedder_backend: str = "ollama"
    embedder_model: str = "nomic-embed-text"
    chunk_size: int = 40
    repo: str = "."
    retrieval_strategy: str = "dense"
    bm25_backend: str = "memory"
    rerank_model: str = "bge-reranker-base"
    rerank_top_n: int = 20
    llm_model: str = "gpt-4o-mini"
    llm_backend: str = "litellm"
    observability_backend: str = "none"
    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    qdrant_url: str = ":memory:"
    qdrant_collection: str = "coderag"
    qdrant_distance: str = "Cosine"
    vector_store: str = "pgvector"
