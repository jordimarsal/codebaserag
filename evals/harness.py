import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from coderag.generation.generator import GenerationError
from coderag.types import Answer, RetrievalResult
from evals.dataset import EvalError, GoldenEntry
from evals.metrics import ndcg_at_k, recall_at_k, reciprocal_rank


# region EntryResult
@dataclass
class EntryResult:
    entry: GoldenEntry
    retrieved_files: list[str]
    recall: float
    mrr: float
    ndcg: float


# region EvalReport
@dataclass
class EvalReport:
    entries: list[EntryResult]
    mean_recall: float
    mean_mrr: float
    mean_ndcg: float
    top_k: int

    def to_markdown(self) -> str:
        lines = [
            "| Metric | Value |",
            "|---------|-------|",
            f"| mean recall@{self.top_k} | {self.mean_recall:.3f} |",
            f"| mean MRR | {self.mean_mrr:.3f} |",
            f"| mean nDCG@{self.top_k} | {self.mean_ndcg:.3f} |",
        ]
        return "\n".join(lines)


# region run_retrieval_eval
def run_retrieval_eval(
    entries: list[GoldenEntry],
    retriever: Callable[[str], list[RetrievalResult]],
    *,
    top_k: int = 5,
) -> EvalReport:
    if not entries:
        raise EvalError("cannot run retrieval eval on an empty dataset")
    results: list[EntryResult] = []
    for entry in entries:
        retrieved = retriever(entry.question)
        files = [item.chunk.path for item in retrieved]
        if len(retrieved) > top_k:
            raise EvalError(
                f"retriever returned {len(retrieved)} results, expected at most top_k={top_k}"
            )
        relevant = set(entry.expected_files)
        results.append(
            EntryResult(
                entry=entry,
                retrieved_files=files,
                recall=recall_at_k(files, relevant, top_k),
                mrr=reciprocal_rank(files, relevant),
                ndcg=ndcg_at_k(files, relevant, top_k),
            )
        )
    count = len(results)
    return EvalReport(
        entries=results,
        mean_recall=sum(r.recall for r in results) / count,
        mean_mrr=sum(r.mrr for r in results) / count,
        mean_ndcg=sum(r.ndcg for r in results) / count,
        top_k=top_k,
    )


# region experiment_markdown
def experiment_markdown(reports: dict[str, EvalReport]) -> str:
    header = ["strategy", "recall@5", "MRR", "nDCG@5"]
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
    ]
    for name in sorted(reports):
        report = reports[name]
        lines.append(
            f"| {name} | {report.mean_recall:.3f} | {report.mean_mrr:.3f} | "
            f"{report.mean_ndcg:.3f} |"
        )
    return "\n".join(lines)


# region GenEntryResult
@dataclass
class GenEntryResult:
    entry: GoldenEntry
    grounded: bool
    schema_ok: bool
    contains: bool


# region GenerationReport
@dataclass
class GenerationReport:
    entries: list[GenEntryResult]
    grounding_rate: float
    schema_rate: float
    contains_rate: float
    top_k: int

    def to_markdown(self) -> str:
        lines = [
            "| Metric | Value |",
            "|---------|-------|",
            f"| grounding rate | {self.grounding_rate:.3f} |",
            f"| schema-conformance rate | {self.schema_rate:.3f} |",
            f"| answer-contains rate | {self.contains_rate:.3f} |",
        ]
        return "\n".join(lines)


# region run_generation_eval
def run_generation_eval(
    entries: list[GoldenEntry],
    retriever: Callable[[str], list[RetrievalResult]],
    generator: "GenerationCallable",
    *,
    top_k: int = 5,
) -> GenerationReport:
    if not entries:
        raise EvalError("cannot run generation eval on an empty dataset")
    if top_k < 1:
        raise EvalError("top_k must be >= 1")
    results: list[GenEntryResult] = []
    for entry in entries:
        retrieved = retriever(entry.question)
        if len(retrieved) > top_k:
            raise EvalError(
                f"retriever returned {len(retrieved)} results, expected at most top_k={top_k}"
            )
        grounded = False
        schema_ok = False
        contains = False
        try:
            answer = generator(entry.question, retrieved)
        except GenerationError:
            answer = None
        if answer is not None:
            schema_ok = True
            grounded = bool(answer.payload.get("grounded", False))
            contains = all(token in answer.text for token in entry.answer_contains)
        results.append(
            GenEntryResult(entry=entry, grounded=grounded, schema_ok=schema_ok, contains=contains)
        )
    count = len(results)
    return GenerationReport(
        entries=results,
        grounding_rate=sum(r.grounded for r in results) / count,
        schema_rate=sum(r.schema_ok for r in results) / count,
        contains_rate=sum(r.contains for r in results) / count,
        top_k=top_k,
    )


# region GenerationCallable (structural)
class GenerationCallable(Protocol):
    def __call__(self, question: str, retrieved: list[RetrievalResult]) -> Answer: ...


# region load_baseline
def load_baseline(path: Path) -> dict[str, float]:
    path = Path(path)
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return {key: float(value) for key, value in data.items()}


# region save_baseline
def save_baseline(path: Path, report: EvalReport) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "mean_recall": report.mean_recall,
                "mean_mrr": report.mean_mrr,
                "mean_ndcg": report.mean_ndcg,
                "top_k": report.top_k,
            },
            handle,
            indent=2,
        )


# region assert_not_regressed
def assert_not_regressed(
    report: EvalReport, baseline: dict[str, float], *, adr: str | None = None
) -> None:
    if not baseline:
        return
    threshold = baseline.get("mean_recall")
    if threshold is None:
        return
    if report.mean_recall < threshold:
        reason = (
            f"recall@{report.top_k} regressed: {report.mean_recall:.3f} < "
            f"baseline {threshold:.3f}"
        )
        if adr is None:
            raise AssertionError(f"{reason} (no ADR override provided)")
        reason += f" [ADR override: {adr}]"
        print(f"WARNING: {reason}")
