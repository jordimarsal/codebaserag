import logging

from coderag.retrieval.ports import Reranker
from coderag.types import RetrievalResult

logger = logging.getLogger("coderag.retrieval")


# region CrossEncoderReranker
class CrossEncoderReranker:
    def __init__(self, model: str = "bge-reranker-base", device: str = "cpu") -> None:
        self._model_name = model
        self._device = device
        self._model = None
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(model, device=device)
        except Exception as exc:  # model or dependency unavailable
            logger.warning("reranker model unavailable (%s); falling back to fused ranking", exc)
            self._model = None

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int
    ) -> list[RetrievalResult]:
        if self._model is None or not results:
            return results[:top_k]
        pairs = [(query, result.chunk.text) for result in results]
        scores = self._model.predict(pairs)
        ranked = sorted(
            zip(results, scores, strict=True),
            key=lambda pair: float(pair[1]),
            reverse=True,
        )
        return [result for result, _ in ranked[:top_k]]
