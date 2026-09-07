# Requirements — Phase 0: Setup

## Functional
- R-F0.1: The repository provides a `pyproject.toml` configuring the project and dev tooling.
- R-F0.2: `ruff`, `black`, and `mypy --strict` are configured and runnable.
- R-F0.3: The `src/coderag` package exists with subdomains `ingest`, `retrieval`, `generation`, `stores`, `llm`, `api`.
- R-F0.4: The four ports (`Embedder`, `VectorStore`, `LlmClient`, `Reranker`) are defined as `runtime_checkable` `Protocol`s.
- R-F0.5: Core domain types (`Chunk`, `Citation`, `RetrievalResult`, `Answer`, `Language`, `ChunkStatus`) exist as dataclasses/enums.
- R-F0.6: A trivial test passes; CI runs lint + mypy + tests on every PR.

## Non-functional
- R-F0.7: Code is English-only, fully type-hinted, mypy `--strict` clean.
- R-F0.8: No adapter (pgvector, Qdrant, Ollama, Anthropic, OpenAI, Langfuse) is imported by the core.
