from typing import Protocol, runtime_checkable

from coderag.types import Chunk, RetrievalResult


# region Embedder
@runtime_checkable
class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one dense vector per input text, in order."""
        ...

    def dim(self) -> int:
        """Dimensionality of the produced embeddings."""
        ...


# region VectorStore
@runtime_checkable
class VectorStore(Protocol):
    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Persist chunks alongside their dense vectors."""
        ...

    def query(
        self, vector: list[float], top_k: int, language: object = None
    ) -> list[RetrievalResult]:
        """Return the top_k most similar chunks to the query vector."""
        ...

    def count(self) -> int:
        """Number of indexed chunks."""
        ...
