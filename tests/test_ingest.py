from pathlib import Path

import pytest

from coderag.config import Settings
from coderag.ingest.chunkers import chunk_fixed, chunk_text
from coderag.ingest.pipeline import IngestError, collect_chunks, run_ingest
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


# region ignore-layer hardening (audit: readers.is_ignored-gitignore-root-only-approximation)
def test_discover_files_honors_nested_gitignore(tmp_path: Path):
    sub = tmp_path / "config"
    sub.mkdir()
    (sub / ".gitignore").write_text("secrets.yaml\n")
    (sub / "secrets.yaml").write_text("x")
    (sub / "keep.yaml").write_text("x")
    names = {p.name for p in discover_files(tmp_path)}
    assert "secrets.yaml" not in names
    assert "keep.yaml" in names


def test_discover_files_honors_git_info_exclude(tmp_path: Path):
    (tmp_path / ".git" / "info").mkdir(parents=True)
    (tmp_path / ".git" / "info" / "exclude").write_text("excluded.py\n")
    (tmp_path / "excluded.py").write_text("x")
    (tmp_path / "kept.py").write_text("x")
    names = {p.name for p in discover_files(tmp_path)}
    assert "excluded.py" not in names
    assert "kept.py" in names


def test_gitignorespec_does_not_reinclude_under_excluded_dir(tmp_path: Path):
    (tmp_path / ".gitignore").write_text("build/\n!build/keep.py\n")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "keep.py").write_text("x")
    names = {p.name for p in discover_files(tmp_path)}
    assert "keep.py" not in names  # git keeps it excluded; plain PathSpec would not


def test_is_ignored_treats_symlink_outside_root_as_ignored(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    target = tmp_path / "target.py"
    target.write_text("x")
    link = repo / "link.py"
    try:
        link.symlink_to(target)
    except OSError:  # pragma: no cover - platform without symlinks
        pytest.skip("symlinks unavailable")
    (repo / "keep.py").write_text("x")
    names = {p.name for p in discover_files(repo)}
    assert names == {"keep.py"}  # skipped, not an aborting ValueError


# region ingest caps + batching (audit: ingest.run_ingest-unbounded-read-embed-buffering)
def test_collect_chunks_skips_oversized_file(tmp_path: Path):
    (tmp_path / "big.py").write_text("x" * 5000)
    (tmp_path / "small.py").write_text("x = 1")
    chunks = collect_chunks(tmp_path, max_file_bytes=1000)
    assert chunks and all("big.py" not in chunk.path for chunk in chunks)


def test_collect_chunks_raises_when_file_cap_exceeded(tmp_path: Path):
    for i in range(5):
        (tmp_path / f"{i}.py").write_text("x")
    with pytest.raises(IngestError):
        collect_chunks(tmp_path, max_files=3)


def test_collect_chunks_raises_when_total_bytes_cap_exceeded(tmp_path: Path):
    (tmp_path / "a.py").write_text("x" * 300)
    (tmp_path / "b.py").write_text("x" * 300)
    with pytest.raises(IngestError):
        collect_chunks(tmp_path, max_total_bytes=500)


def test_run_ingest_embeds_in_batches(tmp_path: Path):
    for i in range(10):
        (tmp_path / f"{i}.py").write_text(f"valor = {i}")

    class RecordingEmbedder:
        def __init__(self) -> None:
            self.batch_sizes: list[int] = []

        def embed(self, texts: list[str]) -> list[list[float]]:
            self.batch_sizes.append(len(texts))
            return [[0.1, 0.2, 0.3] for _ in texts]

        def dim(self) -> int:
            return 3

    embedder = RecordingEmbedder()
    indexed = run_ingest(tmp_path, embedder, FakeStore(), embed_batch_size=4)
    assert indexed == 10
    assert embedder.batch_sizes == [4, 4, 2]  # no single whole-corpus embed call
