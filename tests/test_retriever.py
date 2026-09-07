from coderag.retrieval.reranker import CrossEncoderReranker
from coderag.retrieval.retriever import RetrievalError, Retriever
from coderag.retrieval.ports import Reranker
from coderag.stores.ports import Embedder, VectorStore
from coderag.types import Chunk, Language, RetrievalResult
from evals.embedder import HashEmbedder


def _chunk(path: str) -> Chunk:
    return Chunk(
        path=path, line_start=1, line_end=1, text=f"body {path}",
        language=Language.PYTHON, hash=f"h-{path}",
    )


class FakeVectorStore:
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks

    def query(self, vector: list[float], top_k: int) -> list[RetrievalResult]:
        return [
            RetrievalResult(chunk=chunk, score=0.5) for chunk in self._chunks[:top_k]
        ]


class FakeBm25:
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks
        self.searched: list[str] = []

    def index(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks

    def search(self, query: str, top_k: int) -> list[RetrievalResult]:
        self.searched.append(query)
        return [
            RetrievalResult(chunk=chunk, score=0.4) for chunk in self._chunks[:top_k]
        ]


class FakeReranker:
    called_with: list[tuple[str, int]] = []

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int
    ) -> list[RetrievalResult]:
        FakeReranker.called_with.append((query, top_k))
        return list(reversed(results))[:top_k]


def _embedder() -> Embedder:
    return HashEmbedder()


# region dense
def test_dense_returns_store_only() -> None:
    store = FakeVectorStore([_chunk("a.py"), _chunk("b.py")])
    bm25 = FakeBm25([_chunk("c.py"), _chunk("d.py")])
    retriever = Retriever(store, bm25, _embedder(), strategy="dense", top_k=5)
    results = retriever.retrieve("q")
    assert [r.chunk.path for r in results] == ["a.py", "b.py"]
    assert bm25.searched == []  # lexical not used in dense


# region hybrid
def test_hybrid_fuses_store_and_bm25() -> None:
    store = FakeVectorStore([_chunk("a.py"), _chunk("b.py")])
    bm25 = FakeBm25([_chunk("c.py"), _chunk("d.py")])
    retriever = Retriever(store, bm25, _embedder(), strategy="hybrid", top_k=5)
    results = retriever.retrieve("q")
    paths = {r.chunk.path for r in results}
    assert paths == {"a.py", "b.py", "c.py", "d.py"}


# region hybrid+rerank
def test_hybrid_rerank_invokes_reranker() -> None:
    FakeReranker.called_with = []
    store = FakeVectorStore([_chunk("a.py"), _chunk("b.py")])
    bm25 = FakeBm25([_chunk("c.py"), _chunk("d.py")])
    retriever = Retriever(
        store, bm25, _embedder(), reranker=FakeReranker(), strategy="hybrid+rerank", top_k=3
    )
    results = retriever.retrieve("q")
    assert FakeReranker.called_with == [("q", 3)]
    assert len(results) <= 3


def test_hybrid_rerank_without_reranker_raises() -> None:
    store = FakeVectorStore([_chunk("a.py")])
    bm25 = FakeBm25([_chunk("c.py")])
    retriever = Retriever(store, bm25, _embedder(), strategy="hybrid+rerank", top_k=5)
    try:
        retriever.retrieve("q")
        raise AssertionError("expected RetrievalError")
    except RetrievalError:
        pass


def test_unknown_strategy_raises() -> None:
    store = FakeVectorStore([_chunk("a.py")])
    bm25 = FakeBm25([_chunk("c.py")])
    retriever = Retriever(store, bm25, _embedder(), strategy="bogus", top_k=5)
    try:
        retriever.retrieve("q")
        raise AssertionError("expected RetrievalError")
    except RetrievalError:
        pass


# region R11 fallback (reranker model unavailable)
def test_reranker_falls_back_when_model_unavailable() -> None:
    reranker = CrossEncoderReranker("bge-reranker-base")  # sentence_transformers likely absent
    if reranker._model is not None:
        import pytest

        pytest.skip("sentence-transformers present; cannot exercise fallback path")
    store = FakeVectorStore([_chunk("a.py"), _chunk("b.py")])
    bm25 = FakeBm25([_chunk("c.py"), _chunk("d.py")])
    retriever = Retriever(
        store, bm25, _embedder(), reranker=reranker, strategy="hybrid+rerank", top_k=3
    )
    results = retriever.retrieve("q")
    assert len(results) <= 3
    assert {r.chunk.path for r in results} <= {"a.py", "b.py", "c.py", "d.py"}
