import math

from coderag.types import Chunk, RetrievalResult


# region bm25_term_score
def bm25_term_score(
    tf: int, df: int, n_docs: int, dl: int, avgdl: float, k1: float = 1.5, b: float = 0.75
) -> float:
    idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
    denominator = tf + k1 * (1.0 - b + b * (dl / avgdl if avgdl > 0 else 1.0))
    return idf * (tf * (k1 + 1.0)) / denominator


def _chunk_key(chunk: Chunk) -> tuple[str, int, int, str]:
    return (chunk.path, chunk.line_start, chunk.line_end, chunk.hash)


# region reciprocal_rank_fusion
def reciprocal_rank_fusion(
    rankings: list[list[RetrievalResult]], k: int = 60
) -> list[RetrievalResult]:
    if not rankings:
        return []
    fused: dict[tuple[str, int, int, str], float] = {}
    best_chunk: dict[tuple[str, int, int, str], Chunk] = {}
    for ranking in rankings:
        for rank, result in enumerate(ranking, start=1):
            key = _chunk_key(result.chunk)
            fused[key] = fused.get(key, 0.0) + 1.0 / (k + rank)
            best_chunk.setdefault(key, result.chunk)
    ordered = sorted(fused.items(), key=lambda pair: pair[1], reverse=True)
    return [
        RetrievalResult(chunk=chunk, score=score) for key, score, chunk in
        ((key, score, best_chunk[key]) for key, score in ordered)
    ]
