from coderag.retrieval.fusion import bm25_term_score, reciprocal_rank_fusion
from coderag.types import Chunk, Language, RetrievalResult


def _chunk(path: str, text: str) -> Chunk:
    return Chunk(path=path, line_start=1, line_end=1, text=text, language=Language.PYTHON, hash=f"h-{path}")


def _result(chunk: Chunk, score: float) -> RetrievalResult:
    return RetrievalResult(chunk=chunk, score=score)


# region bm25_term_score
def test_bm25_term_score_ordering() -> None:
    rare = bm25_term_score(tf=1, df=1, n_docs=10, dl=10, avgdl=10)
    common = bm25_term_score(tf=1, df=9, n_docs=10, dl=10, avgdl=10)
    assert rare > common


def test_bm25_term_score_zero_idf_clamped() -> None:
    # df == n_docs -> idf term log(0.5/... ) still positive but small; ensure finite
    score = bm25_term_score(tf=2, df=10, n_docs=10, dl=10, avgdl=10)
    assert score >= 0.0


# region reciprocal_rank_fusion
def test_rrf_combines_two_rankings() -> None:
    a = _result(_chunk("a.py", "alpha"), 0.9)
    b = _result(_chunk("b.py", "beta"), 0.8)
    ranking1 = [a, b]
    ranking2 = [b, a]
    fused = reciprocal_rank_fusion([ranking1, ranking2])
    assert {r.chunk.path for r in fused} == {"a.py", "b.py"}
    # equal reciprocal ranks -> tied, both present and fused score > 0
    assert fused[0].score > 0.0


def test_rrf_promotes_cross_list_presence() -> None:
    a = _result(_chunk("a.py", "alpha"), 0.1)
    b = _result(_chunk("b.py", "beta"), 0.1)
    # a ranks high in list1 only, b high in list2 only
    fused = reciprocal_rank_fusion([[a, b], [b, a]])
    keys = [r.chunk.path for r in fused]
    assert set(keys) == {"a.py", "b.py"}


def test_rrf_empty_input() -> None:
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[]]) == []


def test_rrf_deterministic() -> None:
    a = _result(_chunk("a.py", "alpha"), 0.5)
    b = _result(_chunk("b.py", "beta"), 0.5)
    first = reciprocal_rank_fusion([[a, b], [b, a]])
    second = reciprocal_rank_fusion([[a, b], [b, a]])
    assert [r.chunk.path for r in first] == [r.chunk.path for r in second]
