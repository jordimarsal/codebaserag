import os

import pytest

from coderag.stores.pgvector import PgvectorStore, StoreError
from coderag.types import Chunk, Language

pytestmark = pytest.mark.skipif(
    not os.environ.get("CODERAG_TEST_DB"),
    reason="no live pgvector database (set CODERAG_TEST_DB to enable)",
)


def _store() -> PgvectorStore:
    dsn = os.environ["CODERAG_TEST_DB"]
    store = PgvectorStore(dsn, dim=3)
    with store._connect() as conn:  # noqa: SLF001 - test teardown
        conn.execute("DELETE FROM chunks")
    return store


def _chunks() -> list[Chunk]:
    return [
        Chunk("a.py", 1, 1, "alpha", Language.PYTHON, "h1"),
        Chunk("b.py", 2, 2, "beta", Language.PYTHON, "h2"),
        Chunk("c.md", 3, 3, "gamma", Language.MARKDOWN, "h3"),
    ]


def test_upsert_query_count_and_ordering():
    store = _store()
    chunks = _chunks()
    store.upsert(chunks, [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])

    results = store.query([1.0, 0.0, 0.0], top_k=2)
    assert len(results) == 2
    assert results[0].chunk.path == "a.py"
    assert results[0].score >= results[1].score

    assert store.count() == 3


def test_query_returns_empty_for_no_match():
    store = _store()
    assert store.query([0.5, 0.5, 0.5], top_k=5) == []


def test_store_error_on_bad_dsn():
    with pytest.raises(StoreError):
        PgvectorStore("postgresql://nope:nope@localhost:1/nope", dim=3)
