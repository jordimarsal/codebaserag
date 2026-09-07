from typing import Protocol, runtime_checkable

from coderag.types import RetrievalResult


# region Reranker
@runtime_checkable
class Reranker(Protocol):
    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int
    ) -> list[RetrievalResult]:
        """Reorder retrieval results by relevance and keep the top_k."""
        ...
