import logging

from coderag.types import RetrievalResult

logger = logging.getLogger("coderag.retrieval")


# region parse_model_ref
def parse_model_ref(model: str) -> "tuple[str, str | None]":
    """Split a ``model-id@revision`` reference into ``(model_id, revision)``.

    A bare id resolves against the Hugging Face Hub at the mutable default ref
    inside the serving process, so whoever controls the upstream repo content
    can change the model without any source review (audit finding
    reranker.unpinned-hub-model-load). ``org/model@<commit-or-tag>`` pins it.
    """
    if "@" not in model:
        return model, None
    model_id, _, revision = model.partition("@")
    return model_id, revision or None


# region CrossEncoderReranker
class CrossEncoderReranker:
    def __init__(self, model: str = "bge-reranker-base", device: str = "cpu") -> None:
        model_id, revision = parse_model_ref(model)
        self._model_name = model
        self._device = device
        self._model = None
        if revision is None:
            logger.warning(
                "reranker model %r has no @revision pin: it resolves against the "
                "Hub's mutable default ref; set CODERAG_RERANK_MODEL='org/model@<commit>'",
                model,
            )
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(model_id, revision=revision, device=device)
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
