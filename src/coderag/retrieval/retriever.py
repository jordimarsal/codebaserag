import logging
from collections.abc import Iterator
from contextlib import contextmanager

from coderag.observability.ports import Span, Tracer
from coderag.retrieval.bm25 import Bm25Index
from coderag.retrieval.fusion import reciprocal_rank_fusion
from coderag.retrieval.ports import Reranker
from coderag.stores.ports import Embedder, VectorStore
from coderag.types import RetrievalResult

logger = logging.getLogger("coderag.retrieval")

# Request-independent bounds (audit findings api-query-topk-unbounded-limit,
# bm25.pgfts-unbounded-limit-full-rank-fetchall): even trusted CLI callers get a
# ceiling, so a mistyped --top-k cannot turn one retrieval into an unbounded
# store scan / LIMIT / rerank fan-out. The API schema bounds requests further.
MAX_TOP_K = 100
MAX_CANDIDATE_K = 200


# region RetrievalError
class RetrievalError(Exception):
    """Raised when retrieval cannot be completed."""


# region Retriever
class Retriever:
    def __init__(
        self,
        store: VectorStore,
        bm25: Bm25Index,
        embedder: Embedder,
        *,
        reranker: Reranker | None = None,
        strategy: str = "dense",
        top_k: int = 5,
        rerank_top_n: int = 20,
        tracer: Tracer | None = None,
    ) -> None:
        self._store = store
        self._bm25 = bm25
        self._embedder = embedder
        self._reranker = reranker
        self._strategy = strategy
        self._top_k = max(1, min(int(top_k), MAX_TOP_K))
        self._rerank_top_n = max(1, min(int(rerank_top_n), MAX_TOP_K))
        self._tracer = tracer

    @contextmanager
    def _trace(self, name: str, **attributes: object) -> Iterator[Span]:
        if self._tracer is None:
            yield Span(name, **attributes)
            return
        try:
            with self._tracer.span(name, **attributes) as span:
                yield span
        except Exception as exc:  # non-blocking (R8)
            logger.warning("tracer failed for span %s: %s", name, exc)
            yield Span(name, **attributes)

    def retrieve(self, question: str) -> list[RetrievalResult]:
        if self._strategy == "dense":
            with self._trace("retrieval", strategy="dense", top_k=self._top_k) as span:
                results = self._store.query(self._embed(question), self._top_k)
                span.set(candidate_count=len(results))
            return results
        if self._strategy not in ("hybrid", "hybrid+rerank"):
            raise RetrievalError(f"unknown retrieval strategy: {self._strategy}")

        candidate_k = min(max(self._top_k, self._rerank_top_n), MAX_CANDIDATE_K)
        with self._trace("retrieval", strategy=self._strategy, top_k=self._top_k) as span:
            dense = self._store.query(self._embed(question), candidate_k)
            lexical = self._bm25.search(question, candidate_k)
            fused = reciprocal_rank_fusion([dense, lexical])
            span.set(candidate_count=len(fused))
        if self._strategy == "hybrid":
            return fused[: self._top_k]
        # hybrid+rerank
        if self._reranker is None:
            raise RetrievalError("strategy hybrid+rerank requires a configured Reranker")
        with self._trace("rerank", input_count=len(fused), top_k=self._top_k) as span:
            reranked = self._reranker.rerank(question, fused, self._top_k)
            span.set(output_count=len(reranked))
        return reranked

    def _embed(self, question: str) -> list[float]:
        return self._embedder.embed([question])[0]
