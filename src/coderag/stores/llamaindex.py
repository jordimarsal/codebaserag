"""LlamaIndex vector store adapter (optional dependency: llama-index-core).

Same `VectorStore` port, same cosine semantics as the in-memory store: the
corpus, the vectors and the embedder stay the project's own — llama-index is
only the query layer (C1: LangChain-ecosystem retrieval). Score parity with the
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

    def _embedding(self, vector: list[float]) -> list[float]:
        """Return the vector padded with a sentinel dimension.

        llama-index computes cosine as dot / (norm * norm) and yields `nan` for
        a zero vector. `SimpleVectorStore` ranks with a heap, and a `nan`
        breaks the heap invariant: valid candidates get dropped and the top-k
        stops being the top-k. Mapping a zero vector to the sentinel axis makes
        its cosine exactly 0.0 for every query (dot == 0, norm == 1), which is
        what `InMemoryVectorStore` returns for the same input.
        """
        values = list(vector)
        values.append(1.0 if all(value == 0.0 for value in values) else 0.0)
        return values

    def _result(self, node: TextNode, score: float) -> RetrievalResult:
        metadata = node.metadata
        try:
            chunk = Chunk(
                path=str(metadata.get("path", "")),
                line_start=int(metadata.get("line_start", 0)),
                line_end=int(metadata.get("line_end", 0)),
                text=node.get_content(),
                language=Language(str(metadata.get("language", "unknown"))),
                hash=str(metadata.get("hash", node.node_id)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise StoreError(f"llama-index node decode failed: {exc}") from exc
        score_value = float(score)
        if not math.isfinite(score_value):
            score_value = 0.0  # defensive: the sentinel padding keeps scores finite
        return RetrievalResult(chunk=chunk, score=score_value)

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise StoreError("chunks and vectors length mismatch")
        # The content hash alone is not a unique node id: two files can hold
        # identical text (an empty __init__.py and an empty README line do).
        # Qdrant keys points by path+lines+hash; mirror that here so the store
        # keeps every chunk instead of silently collapsing the duplicates.
        nodes = [
            TextNode(
                id_=f"{chunk.path}:{chunk.line_start}:{chunk.line_end}:{chunk.hash}",
                text=chunk.text,
                metadata={
                    "path": chunk.path,
                    "line_start": chunk.line_start,
                    "line_end": chunk.line_end,
                    "language": chunk.language.value,
                    "hash": chunk.hash,
                },
                embedding=self._embedding(vector),
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        self._store.add(nodes)
        for node in nodes:
            self._nodes[node.node_id] = node

    def query(self, vector: list[float], top_k: int) -> list[RetrievalResult]:
        if all(value == 0.0 for value in vector):
            # A zero query scores 0.0 against everything; mirror the in-memory
            # stable order instead of feeding a zero norm to llama-index.
            nodes = list(self._nodes.values())[:top_k]
            return [self._result(node, 0.0) for node in nodes]
        query = VectorStoreQuery(query_embedding=self._embedding(vector), similarity_top_k=top_k)
        result = self._store.query(query)
        ids = result.ids or []
        scores = result.similarities or []
        results: list[RetrievalResult] = []
        for node_id, similarity in zip(ids, scores, strict=False):
            node = self._nodes.get(node_id)
            if node is None:
                raise StoreError(f"llama-index node {node_id} not found")
            results.append(self._result(node, similarity))
        return results

    def count(self) -> int:
        return len(self._nodes)


# endregion
