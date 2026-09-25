import logging
import re
from typing import Any, Protocol, runtime_checkable

from coderag.types import Chunk, Language, RetrievalResult

logger = logging.getLogger("coderag.retrieval")


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


# region Bm25Index
@runtime_checkable
class Bm25Index(Protocol):
    def index(self, chunks: list[Chunk]) -> None:
        """Build the lexical index from the given chunks."""
        ...

    def search(self, query: str, top_k: int) -> list[RetrievalResult]:
        """Return the top_k chunks for the query by lexical relevance."""
        ...


# region InMemoryBm25
class InMemoryBm25:
    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._terms: list[list[str]] = []
        self._df: dict[str, int] = {}
        self._avgdl: float = 0.0

    def index(self, chunks: list[Chunk]) -> None:
        self._chunks = list(chunks)
        self._terms = [_tokenize(c.text) for c in chunks]
        df: dict[str, int] = {}
        for terms in self._terms:
            for term in set(terms):
                df[term] = df.get(term, 0) + 1
        self._df = df
        total = sum(len(t) for t in self._terms)
        self._avgdl = total / len(self._terms) if self._terms else 0.0

    def search(self, query: str, top_k: int) -> list[RetrievalResult]:
        from coderag.retrieval.fusion import bm25_term_score

        query_terms = _tokenize(query)
        if not self._terms or not query_terms:
            return []
        scored: list[tuple[Chunk, float]] = []
        for chunk, terms in zip(self._chunks, self._terms, strict=True):
            dl = len(terms)
            tf_by_term: dict[str, int] = {}
            for term in terms:
                tf_by_term[term] = tf_by_term.get(term, 0) + 1
            score = 0.0
            for term in query_terms:
                if term in self._df:
                    score += bm25_term_score(
                        tf_by_term.get(term, 0),
                        len(self._chunks),
                        self._df[term],
                        dl,
                        self._avgdl,
                    )
            if score > 0.0:
                scored.append((chunk, score))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [RetrievalResult(chunk=chunk, score=score) for chunk, score in scored[:top_k]]


# region TantivyBm25
class TantivyBm25:
    def __init__(self, index_dir: str = ".bm25_index") -> None:
        import tantivy  # lazy: optional dependency

        self._tantivy: Any = tantivy
        self._index_dir = index_dir
        self._index: Any = None

    def index(self, chunks: list[Chunk]) -> None:
        schema = self._tantivy.SchemaBuilder()
        schema.add_text_field("path", stored=True)
        schema.add_text_field("body", stored=True)
        index = self._tantivy.Index(schema.build(), self._index_dir)
        writer: Any = index.writer()
        for chunk in chunks:
            writer.add_document(
                path=chunk.path, body=chunk.text, _id=f"{chunk.path}:{chunk.line_start}"
            )
        writer.commit()
        self._index = index

    def search(self, query: str, top_k: int) -> list[RetrievalResult]:
        if self._index is None:
            return []
        searcher = self._index.searcher()
        query_obj = self._tantivy.Query.parse("body:" + query)
        results = searcher.search(query_obj, limit=top_k)
        output: list[RetrievalResult] = []
        for hit in results.hits:
            doc = searcher.doc(hit.doc_id)
            path = doc.get_first("path") or ""
            output.append(
                RetrievalResult(
                    chunk=Chunk(
                        path=path,
                        line_start=0,
                        line_end=0,
                        text="",
                        language=chunk_lang(path),
                        hash="",  # not stored in the tantivy schema
                    ),
                    score=float(hit.score),
                )
            )
        return output


def chunk_lang(path: str) -> "Language":
    from pathlib import Path

    from coderag.ingest.readers import language_for

    return language_for(Path(path))


# region PostgresFtsBm25
class PostgresFtsBm25:
    def __init__(self, dsn: str) -> None:
        import psycopg

        self._psycopg = psycopg
        self._dsn = dsn

    def index(self, chunks: list[Chunk]) -> None:
        logger.info("PostgresFtsBm25 uses the existing chunks table; no separate index build.")

    def search(self, query: str, top_k: int) -> list[RetrievalResult]:
        from coderag.types import Language

        with self._psycopg.connect(self._dsn, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT path, line_start, line_end, text, language, hash, "
                "ts_rank(to_tsvector('english', text), plainto_tsquery('english', %s)) AS rank "
                "FROM chunks "
                "WHERE to_tsvector('english', text) @@ plainto_tsquery('english', %s) "
                "ORDER BY rank DESC LIMIT %s",
                (query, query, top_k),
            )
            return [
                RetrievalResult(
                    chunk=Chunk(
                        path=row[0],
                        line_start=row[1],
                        line_end=row[2],
                        text=row[3],
                        language=Language(row[4]),
                        hash=row[5],
                    ),
                    score=float(row[6]),
                )
                for row in cur.fetchall()
            ]
