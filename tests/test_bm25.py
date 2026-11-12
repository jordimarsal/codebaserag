"""In-memory BM25: the lexical half of hybrid retrieval."""

from coderag.retrieval.bm25 import InMemoryBm25
from coderag.types import Chunk, Language


def _chunk(path: str, text: str) -> Chunk:
    return Chunk(
        path=path,
        line_start=1,
        line_end=1,
        text=text,
        language=Language.PYTHON,
        hash=f"h-{path}",
    )


def test_search_ranks_the_document_that_contains_the_query_term() -> None:
    index = InMemoryBm25()
    index.index(
        [
            _chunk("role.py", "the role registry maps a role to a model"),
            _chunk("other.py", "beta gamma"),
        ]
    )

    results = index.search("role model", top_k=5)

    assert results
    assert results[0].chunk.path == "role.py"
    assert results[0].score > 0.0


def test_search_returns_nothing_when_no_term_matches() -> None:
    index = InMemoryBm25()
    index.index([_chunk("a.py", "alpha beta"), _chunk("b.py", "gamma delta")])

    assert index.search("nonexistent", top_k=5) == []


def test_search_prefers_the_rarer_query_term() -> None:
    index = InMemoryBm25()
    index.index(
        [
            _chunk("common1.py", "cache cache cache cache"),
            _chunk("common2.py", "cache cache cache cache"),
            _chunk("rare.py", "cache invalidation"),
        ]
    )

    results = index.search("cache invalidation", top_k=5)

    assert results[0].chunk.path == "rare.py"
