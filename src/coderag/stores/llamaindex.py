"""LlamaIndex vector store adapter (optional dependency: llama-index-core).

Same `VectorStore` port, same cosine semantics as the in-memory store: the
corpus, the vectors and the embedder stay the project's own — llama-index is
only the query layer (C1: LangChain-ecosystem retrieval). Parity with the
in-memory backend is checked by `evals/experiments/llamaindex_vs_dense.py`;
retrieval quality stays gated by the project's own eval baseline.
"""

import math

from llama_index.core.schema import TextNode
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.core.vector_stores.types import VectorStoreQuery

from coderag.stores.errors import StoreError
from coderag.types import Chunk, Language, RetrievalResult


# region LlamaIndexStore
class LlamaIndexStore:
    """`VectorStore` port backed by llama-index's `SimpleVectorStore`."""

    def __init__(self, dim: int) -> None:
        self._dim = dim
        self._store = SimpleVectorStore()
        self._nodes: dict[str, TextNode] = {}

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise StoreError("chunks and vectors length mismatch")
        nodes = [
            TextNode(
                id_=chunk.hash,
                text=chunk.text,
                metadata={
                    "path": chunk.path,
                    "line_start": chunk.line_start,
                    "line_end": chunk.line_end,
                    "language": chunk.language.value,
                },
                embedding=list(vector),
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        self._store.add(nodes)
        for node in nodes:
            self._nodes[node.node_id] = node

    def query(self, vector: list[float], top_k: int) -> list[RetrievalResult]:
        query = VectorStoreQuery(query_embedding=list(vector), similarity_top_k=top_k)
        result = self._store.query(query)
        ids = result.ids or []
        scores = result.similarities or []
        results: list[RetrievalResult] = []
        for node_id, similarity in zip(ids, scores, strict=False):
            node = self._nodes.get(node_id)
            if node is None:
                raise StoreError(f"llama-index node {node_id} not found")
            metadata = node.metadata
            try:
                chunk = Chunk(
                    path=str(metadata.get("path", "")),
                    line_start=int(metadata.get("line_start", 0)),
                    line_end=int(metadata.get("line_end", 0)),
                    text=node.get_content(),
                    language=Language(str(metadata.get("language", "unknown"))),
                    hash=node.node_id,
                )
                score_value = float(similarity)
                if not math.isfinite(score_value):
                    score_value = 0.0  # zero-norm vectors: parity amb InMemoryVectorStore
            except (KeyError, TypeError, ValueError) as exc:
                raise StoreError(f"llama-index node decode failed: {exc}") from exc
            results.append(RetrievalResult(chunk=chunk, score=score_value))
        return results

    def count(self) -> int:
        return len(self._nodes)


# endregion
