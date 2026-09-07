from pathlib import Path

import pytest

from coderag.config import Settings
from coderag.ingest.chunkers import chunk_fixed, chunk_text
from coderag.ingest.pipeline import IngestError, run_ingest
from coderag.ingest.readers import discover_files, is_ignored, language_for, load_gitignore
from coderag.stores.ports import Embedder, VectorStore
from coderag.types import Chunk, Language, RetrievalResult


# region fixtures
class FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

    def dim(self) -> int:
        return 3


class FakeStore:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self.vectors: list[list[float]] = []

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        self.chunks = chunks
        self.vectors = vectors

    def query(
        self, vector: list[float], top_k: int, language: object = None
    ) -> list[RetrievalResult]:
        return []

    def count(self) -> int:
        return len(self.chunks)


# region R3 language mapping
def test_language_for_maps_extensions():
    assert language_for(Path("a.py")) is Language.PYTHON
    assert language_for(Path("a.md")) is Language.MARKDOWN
    assert language_for(Path("a.toml")) is Language.TOML
    assert language_for(Path("a.yaml")) is Language.YAML
    assert language_for(Path("a.txt")) is Language.UNKNOWN


# region R1 extension filter
def test_discover_files_filters_by_extension(tmp_path: Path):
    (tmp_path / "a.py").write_text("x")
    (tmp_path / "b.md").write_text("x")
    (tmp_path / "c.txt").write_text("x")
    names = {p.name for p in discover_files(tmp_path)}
    assert names == {"a.py", "b.md"}


# region R2 gitignore + .git skip
def test_discover_files_skips_gitignore_and_git_dir(tmp_path: Path):
    (tmp_path / ".gitignore").write_text("secret.py\n")
    (tmp_path / "secret.py").write_text("x")
    (tmp_path / "keep.py").write_text("x")
    git_dir = tmp_path / ".git" / "x"
    git_dir.mkdir(parents=True)
    (git_dir / "y.py").write_text("x")
    names = {p.name for p in discover_files(tmp_path)}
    assert "secret.py" not in names
    assert "keep.py" in names
    assert (git_dir / "y.py") not in [p.resolve() for p in discover_files(tmp_path)]


def test_is_ignored_direct(tmp_path: Path):
    (tmp_path / ".gitignore").write_text("build/\n")
    spec = load_gitignore(tmp_path)
    assert is_ignored(tmp_path / "build" / "out.py", tmp_path, spec) is True
    assert is_ignored(tmp_path / "src" / "main.py", tmp_path, spec) is False


# region R4 fixed chunking spans
def test_chunk_fixed_line_spans_and_hash():
    text = "\n".join(f"line{i}" for i in range(10))
    chunks = chunk_fixed(text, "f.py", Language.PYTHON, size=4)
    assert chunks[0].line_start == 1
    assert chunks[0].line_end == 4
    assert chunks[-1].line_end == 10
    assert chunks[0].hash != chunks[1].hash
    assert all(c.language is Language.PYTHON for c in chunks)


def test_chunk_fixed_empty_file():
    chunks = chunk_fixed("", "empty.py", Language.PYTHON, size=4)
    assert len(chunks) == 1
    assert chunks[0].text == ""


# region chunk_text dispatcher
def test_chunk_text_unknown_strategy_raises():
    with pytest.raises(ValueError):
        chunk_text("x", "f.py", Language.PYTHON, strategy="nope")


# region R6/R10 pipeline end-to-end (core, no adapters)
def test_pipeline_end_to_end(tmp_path: Path):
    (tmp_path / "a.py").write_text("x = 1\ny = 2\n")
    embedder = FakeEmbedder()
    store = FakeStore()
    indexed = run_ingest(tmp_path, embedder, store)
    assert indexed >= 1
    assert store.chunks and len(store.chunks) == indexed
    assert all(isinstance(c, Chunk) for c in store.chunks)


# region R11 error isolation
def test_pipeline_skips_binary_file(tmp_path: Path):
    (tmp_path / "good.py").write_text("x = 1")
    (tmp_path / "bad.py").write_bytes(b"\xff\xfe\x00\x01")
    indexed = run_ingest(tmp_path, FakeEmbedder(), FakeStore())
    assert indexed == 1


def test_pipeline_raises_on_embedding_error(tmp_path: Path):
    (tmp_path / "a.py").write_text("x = 1")

    class BrokenEmbedder:
        def embed(self, texts: list[str]) -> list[list[float]]:
            raise RuntimeError("boom")

        def dim(self) -> int:
            return 3

    with pytest.raises(IngestError):
        run_ingest(tmp_path, BrokenEmbedder(), FakeStore())


# region R10 port conformance
def test_ports_are_runtime_checkable():
    assert isinstance(FakeEmbedder(), Embedder)
    assert isinstance(FakeStore(), VectorStore)


# region R12 environment configuration
def test_settings_reads_env_with_prefix(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CODERAG_CHUNK_SIZE", "17")
    monkeypatch.setenv("CODERAG_DATABASE_DSN", "postgresql://test:1/test")
    settings = Settings()
    assert settings.chunk_size == 17
    assert settings.database_dsn == "postgresql://test:1/test"
