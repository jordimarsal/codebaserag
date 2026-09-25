from pathlib import Path

import pytest
from evals.dataset import EvalError, GoldenEntry, load_golden
from evals.embedder import HashEmbedder
from evals.harness import (
    EvalReport,
    assert_not_regressed,
    load_baseline,
    run_retrieval_eval,
    save_baseline,
)

from coderag.retrieval.bm25 import InMemoryBm25
from coderag.retrieval.retriever import Retriever
from coderag.stores.memory import InMemoryVectorStore
from coderag.types import Chunk, Language


def _dense_retriever(store: InMemoryVectorStore) -> Retriever:
    return Retriever(store, InMemoryBm25(), HashEmbedder(), strategy="dense", top_k=5)


def _entry(question: str, path: str) -> GoldenEntry:
    return GoldenEntry(
        question=question, expected_files=(path,), answer_contains=("x",), repo="test"
    )


def _seeded_store(texts: list[str], paths: list[str]) -> InMemoryVectorStore:
    embedder = HashEmbedder()
    store = InMemoryVectorStore(dim=embedder.dim())
    chunks = [
        Chunk(
            path=p,
            line_start=1,
            line_end=1,
            text=t,
            language=Language.PYTHON,
            hash=f"h-{i}",
        )
        for i, (t, p) in enumerate(zip(texts, paths, strict=True))
    ]
    store.upsert(chunks, embedder.embed(texts))
    return store


def test_run_retrieval_eval_perfect() -> None:
    entries = [_entry("def f(): pass", "a.py"), _entry("class C: pass", "b.py")]
    store = _seeded_store(["def f(): pass", "class C: pass"], ["a.py", "b.py"])
    report = run_retrieval_eval(entries, _dense_retriever(store).retrieve, top_k=5)
    assert report.mean_recall == 1.0
    assert report.mean_mrr == 1.0
    assert report.mean_ndcg == 1.0


def test_run_retrieval_eval_distractor() -> None:
    entries = [_entry("def f(): pass", "a.py")]
    store = _seeded_store(["def f(): pass", "unrelated noise text here"], ["a.py", "z.py"])
    report = run_retrieval_eval(entries, _dense_retriever(store).retrieve, top_k=5)
    assert report.mean_recall == 1.0
    assert report.entries[0].retrieved_files[0] == "a.py"


def test_run_retrieval_eval_empty_dataset() -> None:
    with pytest.raises(EvalError):
        run_retrieval_eval([], _dense_retriever(_seeded_store(["x"], ["a.py"])).retrieve)


def test_load_golden_from_yaml(tmp_path: Path) -> None:
    yaml_text = """
- question: q1
  expected_files: ["a.py"]
  answer_contains: ["x"]
  repo: r1
- question: q2
  expected_files: ["b.py"]
  answer_contains: ["y"]
  repo: r1
"""
    (tmp_path / "sample.yaml").write_text(yaml_text)
    entries = load_golden(tmp_path)
    assert len(entries) == 2
    assert entries[0].expected_files == ("a.py",)


def test_load_golden_missing_field(tmp_path: Path) -> None:
    (tmp_path / "bad.yaml").write_text("- question: q1\n  repo: r1\n")
    with pytest.raises(EvalError):
        load_golden(tmp_path)


def test_regression_guard_raises_without_adr(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    good = EvalReport([], 1.0, 1.0, 1.0, 5)
    save_baseline(baseline_path, good)
    worse = EvalReport([], 0.2, 0.2, 0.2, 5)
    with pytest.raises(AssertionError):
        assert_not_regressed(worse, load_baseline(baseline_path))


def test_regression_guard_passes_with_adr(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    good = EvalReport([], 1.0, 1.0, 1.0, 5)
    save_baseline(baseline_path, good)
    worse = EvalReport([], 0.2, 0.2, 0.2, 5)
    assert_not_regressed(worse, load_baseline(baseline_path), adr="ADR-009")
