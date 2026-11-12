"""LlamaIndex store adapter: port parity with the in-memory semantics.

Requires the optional `llamaindex` extra (`uv sync --extra llamaindex`);
skipped automatically when it is not installed.
"""

import pytest

pytest.importorskip("llama_index.core")

from coderag.stores.errors import StoreError  # noqa: E402
from coderag.stores.llamaindex import LlamaIndexStore  # noqa: E402
from coderag.types import Chunk, Language  # noqa: E402


def make_chunk(index: int = 0) -> Chunk:
    return Chunk(
        path=f"src/module_{index}.py",
        line_start=index * 10 + 1,
        line_end=index * 10 + 9,
        text=f"Chunk {index}: the answer is {index}.",
        language=Language.PYTHON,
        hash=f"hash-{index:04d}",
    )


def store_with(count: int = 3) -> LlamaIndexStore:
    store = LlamaIndexStore(dim=4)
    chunks = [make_chunk(i) for i in range(count)]
    vectors = [[float(i), 1.0, 0.0, 0.0] for i in range(count)]
    store.upsert(chunks, vectors)
    return store


def test_upsert_counts_indexed_chunks() -> None:
    store = store_with(3)
    assert store.count() == 3


def test_query_returns_the_nearest_chunk_reconstructed() -> None:
    store = store_with(3)

    results = store.query([0.0, 1.0, 0.0, 0.0], top_k=2)

    assert results[0].chunk.hash == "hash-0000"
    assert results[0].chunk.path == "src/module_0.py"
    assert results[0].chunk.line_start == 1
    assert results[0].chunk.line_end == 9
    assert results[0].chunk.text == "Chunk 0: the answer is 0."
    assert len(results) == 2


def test_query_returns_results_sorted_by_similarity() -> None:
    store = store_with(3)

    results = store.query([1.0, 1.0, 0.0, 0.0], top_k=3)

    scores = [result.score for result in results]
    assert scores == sorted(scores, reverse=True)


def test_zero_vector_chunk_scores_zero_without_poisoning_top_k() -> None:
    store = LlamaIndexStore(dim=4)
    chunks = [make_chunk(0), make_chunk(1)]
    store.upsert(chunks, [[0.0, 0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]])

    results = store.query([1.0, 0.0, 0.0, 0.0], top_k=2)

    assert [result.chunk.hash for result in results] == ["hash-0001", "hash-0000"]
    assert [result.score for result in results] == [1.0, 0.0]


def test_zero_query_scores_everything_zero_in_insertion_order() -> None:
    store = store_with(3)

    results = store.query([0.0, 0.0, 0.0, 0.0], top_k=2)

    assert [result.chunk.hash for result in results] == ["hash-0000", "hash-0001"]
    assert [result.score for result in results] == [0.0, 0.0]


def test_duplicate_content_at_different_locations_is_kept() -> None:
    store = LlamaIndexStore(dim=4)
    first = make_chunk(0)
    second = Chunk(
        path="src/other.py",
        line_start=first.line_start,
        line_end=first.line_end,
        text=first.text,
        language=first.language,
        hash=first.hash,
    )
    store.upsert([first, second], [[1.0, 0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]])

    results = store.query([1.0, 0.0, 0.0, 0.0], top_k=2)

    assert store.count() == 2
    assert {result.chunk.path for result in results} == {"src/module_0.py", "src/other.py"}
    assert {result.chunk.hash for result in results} == {first.hash}


def test_empty_index_returns_no_results() -> None:
    store = LlamaIndexStore(dim=4)

    assert store.query([1.0, 0.0, 0.0, 0.0], top_k=3) == []


def test_upsert_rejects_length_mismatch() -> None:
    store = LlamaIndexStore(dim=4)
    chunks = [make_chunk(0)]

    with pytest.raises(StoreError):
        store.upsert(chunks, [[1.0, 0.0], [0.0, 1.0]])
