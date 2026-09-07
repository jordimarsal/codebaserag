from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


# region EvalError
class EvalError(Exception):
    """Raised when the eval dataset or run is invalid."""


# region GoldenEntry
@dataclass(frozen=True)
class GoldenEntry:
    question: str
    expected_files: tuple[str, ...]
    answer_contains: tuple[str, ...]
    repo: str


# region load_golden
def load_golden(directory: Path) -> list[GoldenEntry]:
    directory = Path(directory)
    if not directory.is_dir():
        raise EvalError(f"golden directory not found: {directory}")
    entries: list[GoldenEntry] = []
    for path in sorted(directory.glob("*.yaml")):
        with path.open(encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or []
        if not isinstance(raw, list):
            raise EvalError(f"golden file {path} must contain a YAML list")
        for item in raw:
            entries.append(_parse_entry(item, path))
    if not entries:
        raise EvalError(f"no golden entries found under {directory}")
    return entries


def _parse_entry(item: Any, path: Path) -> GoldenEntry:
    if not isinstance(item, dict):
        raise EvalError(f"golden entry must be a mapping in {path}")
    missing = {"question", "expected_files", "answer_contains", "repo"} - item.keys()
    if missing:
        raise EvalError(f"golden entry missing fields {sorted(missing)} in {path}")
    return GoldenEntry(
        question=str(item["question"]),
        expected_files=tuple(str(f) for f in item["expected_files"]),
        answer_contains=tuple(str(f) for f in item["answer_contains"]),
        repo=str(item["repo"]),
    )
