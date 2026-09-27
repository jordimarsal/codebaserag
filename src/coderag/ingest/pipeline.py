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

# Ingest bounds (audit finding ingest.run_ingest-unbounded-read-embed-buffering):
# one small ingest request used to buffer the full path list, every file's text
# and every chunk in memory, then shipped the whole corpus to the embedder in a
# single call. Defaults bound each file, the file count, the aggregate bytes and
# the embed request size; persistent backends can raise them via settings.
DEFAULT_MAX_FILE_BYTES = 1_000_000
DEFAULT_MAX_FILES = 10_000
DEFAULT_MAX_TOTAL_BYTES = 64_000_000
DEFAULT_EMBED_BATCH_SIZE = 64


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
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_files: int = DEFAULT_MAX_FILES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
) -> list[Chunk]:
    repo_root = Path(repo)
    files = discover_files(repo_root, extensions or DEFAULT_EXTENSIONS)
    if len(files) > max_files:
        raise IngestError(
            f"{len(files)} candidate files exceed the ingest cap (max_files={max_files}); "
            "narrow the repository or raise ingest_max_files"
        )
    chunks: list[Chunk] = []
    total_bytes = 0
    for file in files:
        try:
            size = file.stat().st_size
        except OSError as exc:
            logger.warning("skipping %s: %s", file, exc)
            continue
        if size > max_file_bytes:
            logger.warning(
                "skipping %s: %d bytes exceed max_file_bytes=%d", file, size, max_file_bytes
            )
            continue
        total_bytes += size
        if total_bytes > max_total_bytes:
            raise IngestError(
                f"repository exceeds the ingest cap (max_total_bytes={max_total_bytes}); "
                "narrow the repository or raise ingest_max_total_bytes"
            )
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
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_files: int = DEFAULT_MAX_FILES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    embed_batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
) -> int:
    chunks = collect_chunks(
        repo,
        strategy=strategy,
        extensions=extensions,
        chunk_size=chunk_size,
        max_file_bytes=max_file_bytes,
        max_files=max_files,
        max_total_bytes=max_total_bytes,
    )
    if not chunks:
        logger.info("no chunks produced from %s", Path(repo))
        return 0
    vectors: list[list[float]] = []
    batch_size = max(1, embed_batch_size)
    for start in range(0, len(chunks), batch_size):
        batch = [chunk.text for chunk in chunks[start : start + batch_size]]
        try:
            vectors.extend(embedder.embed(batch))
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
