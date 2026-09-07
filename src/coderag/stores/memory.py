import math

from coderag.types import Chunk, RetrievalResult


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


# region InMemoryVectorStore
class InMemoryVectorStore:
    def __init__(self, dim: int) -> None:
        self._dim = dim
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors length mismatch")
        self._chunks.extend(chunks)
        self._vectors.extend(vectors)

    def query(
        self, vector: list[float], top_k: int, language: object = None
    ) -> list[RetrievalResult]:
        scored = [
            (chunk, _cosine(vector, vec))
            for chunk, vec in zip(self._chunks, self._vectors, strict=True)
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [RetrievalResult(chunk=chunk, score=score) for chunk, score in scored[:top_k]]

    def count(self) -> int:
        return len(self._chunks)
