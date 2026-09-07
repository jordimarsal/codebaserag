from pydantic import BaseModel


# region IngestRequest
class IngestRequest(BaseModel):
    repo: str


# region QueryRequest
class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    strategy: str = "dense"


# region AnswerRequest
class AnswerRequest(BaseModel):
    question: str
    top_k: int = 5
    strategy: str = "dense"


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
