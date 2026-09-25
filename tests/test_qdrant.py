import pytest

from coderag.stores.errors import StoreError
from coderag.stores.qdrant import QdrantVectorStore
from coderag.types import Chunk, Language

pytest.importorskip("qdrant_client")


def _chunks() -> list[Chunk]:
    return [
        Chunk(
            path="a.py",
            line_start=1,
            line_end=3,
            text="def f(): pass",
            language=Language.PYTHON,
            hash="ha",
        ),
        Chunk(
            path="b.py",
            line_start=1,
            line_end=3,
            text="class C: pass",
            language=Language.PYTHON,
            hash="hb",
        ),
    ]


def test_upsert_then_query_reconstructs_chunks() -> None:
    store = QdrantVectorStore(url=":memory:", collection="test1", dim=4, distance="Cosine")
    chunks = _chunks()
    store.upsert(chunks, [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]])
    results = store.query([1.0, 0.0, 0.0, 0.0], top_k=2)
    assert len(results) == 2
    paths = {r.chunk.path for r in results}
    assert paths == {"a.py", "b.py"}
    top = results[0]
    assert top.chunk.language is Language.PYTHON
    assert top.chunk.hash == "ha"
    assert top.score > 0.0


def test_count_reflects_upsert() -> None:
    store = QdrantVectorStore(url=":memory:", collection="test2", dim=2, distance="Cosine")
    assert store.count() == 0
    store.upsert(_chunks(), [[0.1, 0.2], [0.3, 0.4]])
    assert store.count() == 2


def test_missing_client_raises_store_error(monkeypatch) -> None:
    import sys

    monkeypatch.setitem(sys.modules, "qdrant_client", None)
    with pytest.raises(StoreError):
        QdrantVectorStore(url=":memory:", collection="x", dim=2)
