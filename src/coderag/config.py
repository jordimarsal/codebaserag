import os

from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


# region Settings
class Settings(BaseSettings):
    # Audit (config-envfile-cwd-endpoint-override): env_file='.env' resolved
    # against the process CWD let a repository planted with a .env file select
    # the outbound endpoints/DSN of the very process indexing it. Loading a
    # dotenv file is now opt-in via CODERAG_ENV_FILE=<path> (per instantiation,
    # so tests and CLIs can set it at runtime); plain CODERAG_* environment
    # variables keep working everywhere.
    model_config = SettingsConfigDict(env_prefix="CODERAG_", extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        env_file = os.environ.get("CODERAG_ENV_FILE")
        if env_file:
            return (
                init_settings,
                env_settings,
                DotEnvSettingsSource(settings_cls, env_file=env_file),
                file_secret_settings,
            )
        return (init_settings, env_settings, file_secret_settings)

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
    ingest_max_file_bytes: int = 1_000_000
    ingest_max_files: int = 10_000
    ingest_max_total_bytes: int = 64_000_000
