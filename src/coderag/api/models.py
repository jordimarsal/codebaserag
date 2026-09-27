from pydantic import BaseModel, Field


# region IngestRequest
class IngestRequest(BaseModel):
    """Omit `repo` to use the operator-configured scope (`Settings.repo`)."""

    repo: str | None = None


# region Request bounds
#
# Public, unauthenticated scalars are bounded at the schema layer so one small
# request cannot drive unbounded work downstream (audit findings
# api-query-topk-unbounded-limit, bm25.inmemory-search-corpus-scan-x-unbounded-
# query-terms). The retrieval clamp in Retriever is defense in depth on top.
MAX_QUESTION_CHARS = 2000
MAX_TOP_K = 100
STRATEGIES = ("dense", "hybrid", "hybrid+rerank")


# region QueryRequest
class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    top_k: int = Field(default=5, ge=1, le=MAX_TOP_K)
    strategy: str = Field(default="dense", pattern=r"^(dense|hybrid|hybrid\+rerank)$")


# region AnswerRequest
class AnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    top_k: int = Field(default=5, ge=1, le=MAX_TOP_K)
    strategy: str = Field(default="dense", pattern=r"^(dense|hybrid|hybrid\+rerank)$")


# region ChunkOut
class ChunkOut(BaseModel):
    path: str
    line_start: int
    line_end: int
    score: float


# region AnswerOut
class AnswerOut(BaseModel):
    text: str
    citations: list[str]
    confidence: float
    grounded: bool


# region ErrorOut
class ErrorOut(BaseModel):
    error: str
