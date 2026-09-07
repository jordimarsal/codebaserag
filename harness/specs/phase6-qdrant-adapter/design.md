# Design: phase6-qdrant-adapter

## Files to create or modify

- `src/coderag/stores/qdrant.py` — `QdrantVectorStore` implementing `VectorStore`; lazy `qdrant-client`
  import; raises `StoreError` on failure.
- `src/coderag/config.py` — add `qdrant_url: str = ":memory:"`, `qdrant_collection: str = "coderag"`,
  `qdrant_distance: str = "Cosine"`.
- `src/coderag/cli.py` — `build_retriever`/`ingest`/`query` accept `store="qdrant"` and build a
  `QdrantVectorStore` from `Settings`.
- `tests/test_qdrant.py` — in-memory Qdrant round-trip (upsert + query reconstructs chunks); skip when
  `qdrant-client` absent.

## Public signatures

```python
# stores/qdrant.py
class QdrantVectorStore:
    def __init__(
        self,
        url: str = ":memory:",
        collection: str = "coderag",
        dim: int = 64,
        distance: str = "Cosine",
    ) -> None
    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...
    def query(self, vector: list[float], top_k: int) -> list[RetrievalResult]: ...
```

## Point model

- `point_id` = stable `uint64` derived from `md5(f"{path}:{line_start}:{line_end}:{hash}")[:16]`
  (deterministic, replayable across calls; collisions are astronomically unlikely for code chunks).
- `vector` = the provided embedding.
- `payload` = `{"path", "line_start", "line_end", "text", "language", "hash"}` so `query` rebuilds a
  `Chunk`. `language` is stored as its `.value` string and mapped back via `Language(payload["language"])`.

## Distance metric

`QdrantVectorStore.__init__` maps `Settings.qdrant_distance` ("cosine"/"euclid"/"dot") to Qdrant's
`Distance` enum; the collection is (re)created with that metric if it does not exist. Default cosine
matches `InMemoryVectorStore` behaviour so the same embeddings/metrics stay comparable.

## Error handling (R7)

Every Qdrant call is wrapped; on `QdrantException` (or any client error) the adapter raises `StoreError`
with the underlying message, mirroring `PgvectorStore`. The CLI already catches `StoreError`.

## Discarded alternatives

- **Reuse pgvector schema for Qdrant.** Rejected: different backends; the port isolates them.
- **Always run a Qdrant server in tests.** Rejected: `:memory:` mode covers the round-trip offline;
  a server is only needed for distributed/production use (R8).
- **Store vectors without payload, look up text separately.** Rejected: `query` must return full
  `Chunk`s; embedding the payload keeps retrieval self-contained (R5/R6).

## CLI integration (R9)

`build_retriever` gains a `qdrant` branch: `QdrantVectorStore(url=settings.qdrant_url,
collection=settings.qdrant_collection, dim=embedder.dim(), distance=settings.qdrant_distance)`. The
`ingest`/`query`/`eval` `--store` options accept `qdrant` accordingly. Default `qdrant_url=":memory:"`
keeps the offline path working without a server.
