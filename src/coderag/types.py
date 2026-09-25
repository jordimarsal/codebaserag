from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# region Language
class Language(Enum):
    PYTHON = "python"
    MARKDOWN = "markdown"
    TOML = "toml"
    YAML = "yaml"
    UNKNOWN = "unknown"


# region ChunkStatus
class ChunkStatus(Enum):
    PENDING = "PENDING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"


# region Chunk
@dataclass(frozen=True)
class Chunk:
    path: str
    line_start: int
    line_end: int
    text: str
    language: Language
    hash: str
    status: ChunkStatus = ChunkStatus.PENDING


# region Citation
@dataclass(frozen=True)
class Citation:
    path: str
    line_start: int
    line_end: int

    def to_label(self) -> str:
        return f"{self.path}:{self.line_start}-{self.line_end}"


# region RetrievalResult
@dataclass(frozen=True)
class RetrievalResult:
    chunk: Chunk
    score: float


# region Answer
@dataclass(frozen=True)
class Answer:
    text: str
    citations: tuple[Citation, ...]
    confidence: float
    model: str
    confidence_verdict: str = "low"
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        object.__setattr__(
            self,
            "confidence_verdict",
            "high" if self.confidence >= 0.8 else "medium" if self.confidence >= 0.5 else "low",
        )
