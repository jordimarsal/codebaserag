import hashlib

from coderag.stores.errors import StoreError
from coderag.types import Chunk, Language, RetrievalResult

_DISTANCE_ALIASES = {
    "cosine": "Cosine",
    "euclid": "Euclid",
    "dot": "Dot",
}


def _point_id(chunk: Chunk) -> int:
    raw = f"{chunk.path}:{chunk.line_start}:{chunk.line_end}:{chunk.hash}".encode("utf-8")
    return int(hashlib.md5(raw).hexdigest()[:16], 16)


# region QdrantVectorStore
class QdrantVectorStore:
    def __init__(
        self,
        url: str = ":memory:",
        collection: str = "coderag",
        dim: int = 64,
        distance: str = "Cosine",
    ) -> None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
        except ImportError as exc:
            raise StoreError("qdrant-client is not installed") from exc
        self._url = url
        self._collection = collection
        self._dim = dim
        try:
            self._client = (
                QdrantClient(location=url) if url == ":memory:" else QdrantClient(url=url)
            )
        except Exception as exc:
            raise StoreError(f"qdrant connection failed: {exc}") from exc
        qdrant_distance = _DISTANCE_ALIASES.get(distance.lower(), distance)
        try:
            if not self._client.collection_exists(collection):
                self._client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(size=dim, distance=Distance(qdrant_distance)),
                )
        except Exception as exc:  # collection may already exist, or client unavailable
            raise StoreError(f"qdrant collection setup failed: {exc}") from exc

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise StoreError("qdrant upsert: chunks/vectors length mismatch")
        from qdrant_client.models import PointStruct

        points = [
            PointStruct(
                id=_point_id(chunk),
                vector=vector,
                payload={
                    "path": chunk.path,
                    "line_start": chunk.line_start,
                    "line_end": chunk.line_end,
                    "text": chunk.text,
                    "language": chunk.language.value,
                    "hash": chunk.hash,
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        try:
            self._client.upsert(collection_name=self._collection, points=points)
        except Exception as exc:
            raise StoreError(f"qdrant upsert failed: {exc}") from exc

    def query(
        self, vector: list[float], top_k: int, language: object = None
    ) -> list[RetrievalResult]:
        try:
            response = self._client.query_points(
                collection_name=self._collection, query=vector, limit=top_k
            )
        except Exception as exc:
            raise StoreError(f"qdrant query failed: {exc}") from exc
        results: list[RetrievalResult] = []
        for hit in response.points:
            payload = hit.payload or {}
            chunk = Chunk(
                path=str(payload.get("path", "")),
                line_start=int(payload.get("line_start", 0)),
                line_end=int(payload.get("line_end", 0)),
                text=str(payload.get("text", "")),
                language=Language(str(payload.get("language", "unknown"))),
                hash=str(payload.get("hash", "")),
            )
            results.append(RetrievalResult(chunk=chunk, score=float(hit.score)))
        return results

    def count(self) -> int:
        try:
            return self._client.count(collection_name=self._collection).count
        except Exception as exc:
            raise StoreError(f"qdrant count failed: {exc}") from exc
