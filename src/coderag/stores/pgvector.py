import psycopg
from pgvector.psycopg import register_vector
from pgvector.psycopg.vector import Vector

from coderag.stores.errors import StoreError
from coderag.types import Chunk, Language, RetrievalResult


# region PgvectorStore
class PgvectorStore:
    def __init__(self, dsn: str, dim: int) -> None:
        self._dsn = dsn
        self._dim = dim
        self._ensure_schema()

    def _connect(self) -> psycopg.Connection:
        try:
            return psycopg.connect(self._dsn, autocommit=True)
        except psycopg.Error as exc:
            raise StoreError(f"pgvector connect failed: {exc}") from exc

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            register_vector(conn)
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS chunks (
                    id BIGSERIAL PRIMARY KEY,
                    path TEXT NOT NULL,
                    line_start INT NOT NULL,
                    line_end INT NOT NULL,
                    text TEXT NOT NULL,
                    language TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    embedding vector({self._dim})
                )
                """)

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise StoreError("chunks and vectors length mismatch")
        rows = [
            (c.path, c.line_start, c.line_end, c.text, c.language.value, c.hash, Vector(v))
            for c, v in zip(chunks, vectors, strict=True)
        ]
        try:
            with self._connect() as conn:
                register_vector(conn)
                with conn.cursor() as cur:
                    cur.executemany(
                        "INSERT INTO chunks (path, line_start, line_end, text, language, hash, embedding) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        rows,
                    )
        except psycopg.Error as exc:
            raise StoreError(f"upsert failed: {exc}") from exc

    def query(
        self, vector: list[float], top_k: int, language: object = None
    ) -> list[RetrievalResult]:
        try:
            with self._connect() as conn:
                register_vector(conn)
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT path, line_start, line_end, text, language, hash, "
                        "1 - (embedding <=> %s) AS score "
                        "FROM chunks ORDER BY embedding <=> %s LIMIT %s",
                        (Vector(vector), Vector(vector), top_k),
                    )
                    results: list[RetrievalResult] = []
                    for path, ls, le, text, lang, h, score in cur.fetchall():
                        chunk = Chunk(
                            path=path,
                            line_start=ls,
                            line_end=le,
                            text=text,
                            language=Language(lang),
                            hash=h,
                        )
                        results.append(RetrievalResult(chunk=chunk, score=float(score)))
                    return results
        except psycopg.Error as exc:
            raise StoreError(f"query failed: {exc}") from exc

    def count(self) -> int:
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM chunks")
                row = cur.fetchone()
                if row is None:
                    return 0
                return int(row[0])
        except psycopg.Error as exc:
            raise StoreError(f"count failed: {exc}") from exc
