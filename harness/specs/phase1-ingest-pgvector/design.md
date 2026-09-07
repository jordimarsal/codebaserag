# Design: phase1-ingest-pgvector

## Files to create or modify

- `src/coderag/ingest/readers.py` — file discovery honoring `.gitignore` and extension filter.
- `src/coderag/ingest/chunkers.py` — `fixed`, `recursive`, `ast` chunking strategies (at least `fixed` in this phase; `recursive`/`ast` may be stubs returning via `fixed` or raising `NotImplementedError`).
- `src/coderag/ingest/pipeline.py` — orchestrates read → chunk → embed → store.
- `src/coderag/ingest/__init__.py` — expose `read_repo`, `chunk_text`, `run_ingest`.
- `src/coderag/stores/pgvector.py` — `PgvectorStore` adapter implementing `VectorStore`.
- `src/coderag/llm/ollama_embedder.py` — `OllamaEmbedder` implementing `Embedder` (default local).
- `src/coderag/config.py` — `Settings` (pydantic) for DSN and embedder URL with env/.env loading.
- `src/coderag/cli.py` — implement `ingest` and `query` commands (was stubbed).
- `tests/test_ingest.py` — deterministic unit tests for readers/chunkers/pipeline with a fake `Embedder`/`VectorStore`.
- `tests/test_pgvector.py` — integration test gated by a live DB (skipped if absent).

## Public signatures

```python
# readers.py
def discover_files(repo: Path, extensions: frozenset[str]) -> list[Path]
def is_ignored(path: Path, repo_root: Path, ignore_spec) -> bool

# chunkers.py
def chunk_fixed(text: str, path: str, language: Language, *, size: int = 40) -> list[Chunk]
def chunk_text(text: str, path: str, language: Language, strategy: str = "fixed", **kw) -> list[Chunk]

# pipeline.py
def run_ingest(repo: Path, embedder: Embedder, store: VectorStore, *, strategy: str = "fixed", extensions: frozenset[str] | None = None) -> int

# stores/pgvector.py
class PgvectorStore:
    def __init__(self, dsn: str, dim: int) -> None
    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None
    def query(self, vector: list[float], top_k: int, language: object = None) -> list[RetrievalResult]
    def count(self) -> int

# llm/ollama_embedder.py
class OllamaEmbedder:
    def __init__(self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434") -> None
    def embed(self, texts: list[str]) -> list[list[float]]
    def dim(self) -> int

# config.py
class Settings(BaseModel):
    database_dsn: str = "postgresql://localhost:5432/codebaserag"
    embedder_url: str = "http://localhost:11434"
    embedder_model: str = "nomic-embed-text"
    chunk_size: int = 40
```

## Exceptions and error cases

- `IngestError` (domain) raised when a file cannot be read or decoded (R11) — wraps the
  underlying cause, continues with remaining files.
- `StoreError` raised by `PgvectorStore` on connection/query failure (R11).
- `EmbedderError` raised by `OllamaEmbedder` when the endpoint is unreachable or returns
  a non-200 (R11).
- `ConfigurationError` raised by `Settings` when a required variable is missing/invalid (R12).

## Discarded alternatives

- **Storing chunks as raw JSON on disk instead of pgvector.** Rejected: the brief mandates
  pgvector as the default store and requires a swap to Qdrant later; a `VectorStore`
  protocol + pgvector adapter keeps the core unchanged. Disk-JSON would not satisfy R7/R10.
- **Using LangChain/LLamaIndex for ingestion.** Rejected: conflicts with the "pure core,
  I/O at edges, no provider lock-in" principle in `docs/architecture.md`; we keep the core
  dependency-free and only adapters touch third-party SDKs.
