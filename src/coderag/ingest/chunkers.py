import hashlib

from coderag.types import Chunk, Language


# region _hash
def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# region chunk_fixed
def chunk_fixed(text: str, path: str, language: Language, *, size: int = 40) -> list[Chunk]:
    if size <= 0:
        raise ValueError("chunk size must be positive")
    lines = text.splitlines()
    if not lines:
        lines = [""]
    chunks: list[Chunk] = []
    for start in range(0, len(lines), size):
        end = min(start + size, len(lines))
        chunk_text = "\n".join(lines[start:end])
        chunks.append(
            Chunk(
                path=str(path),
                line_start=start + 1,
                line_end=end,
                text=chunk_text,
                language=language,
                hash=_hash(chunk_text),
            )
        )
    return chunks


_STRATEGIES = {"fixed": chunk_fixed}


# region chunk_text
def chunk_text(
    text: str, path: str, language: Language, strategy: str = "fixed", *, size: int = 40
) -> list[Chunk]:
    factory = _STRATEGIES.get(strategy)
    if factory is None:
        raise ValueError(f"unknown chunking strategy: {strategy}")
    return factory(text, path, language, size=size)
