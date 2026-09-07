from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from coderag.ingest.chunkers import chunk_text
from coderag.ingest.readers import DEFAULT_EXTENSIONS, discover_files, language_for

if TYPE_CHECKING:
    from coderag.stores.ports import Embedder, VectorStore
    from coderag.types import Chunk

logger = logging.getLogger("coderag.ingest")


# region IngestError
class IngestError(Exception):
    """Raised when ingestion cannot complete (read, embedding, or store failure)."""


# region collect_chunks
def collect_chunks(
    repo: Path,
    *,
    strategy: str = "fixed",
    extensions: frozenset[str] | None = None,
    chunk_size: int = 40,
) -> list[Chunk]:
    repo_root = Path(repo)
    chunks: list[Chunk] = []
    for file in discover_files(repo_root, extensions or DEFAULT_EXTENSIONS):
        try:
            text = file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("skipping %s: %s", file, exc)
            continue
        language = language_for(file)
        chunks.extend(chunk_text(text, str(file), language, strategy=strategy, size=chunk_size))
    return chunks


# region run_ingest
def run_ingest(
    repo: Path,
    embedder: Embedder,
    store: VectorStore,
    *,
    strategy: str = "fixed",
    extensions: frozenset[str] | None = None,
    chunk_size: int = 40,
) -> int:
    chunks = collect_chunks(
        repo, strategy=strategy, extensions=extensions, chunk_size=chunk_size
    )
    if not chunks:
        logger.info("no chunks produced from %s", Path(repo))
        return 0
    try:
        vectors = embedder.embed([chunk.text for chunk in chunks])
    except Exception as exc:
        raise IngestError(f"embedding failed: {exc}") from exc
    if len(vectors) != len(chunks):
        raise IngestError("embedder returned a different number of vectors than chunks")
    try:
        store.upsert(chunks, vectors)
    except Exception as exc:
        raise IngestError(f"store upsert failed: {exc}") from exc
    logger.info("indexed %d chunks from %s", len(chunks), Path(repo))
    return len(chunks)
