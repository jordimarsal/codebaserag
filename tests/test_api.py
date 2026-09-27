from fastapi.testclient import TestClient

from coderag.api.app import create_app
from coderag.compose import build_retriever
from coderag.config import Settings

SETTINGS = Settings(repo=".", vector_store="memory", llm_backend="fake")


def _client() -> TestClient:
    return TestClient(create_app(SETTINGS))


def test_ingest_then_query_round_trip() -> None:
    client = _client()
    ingest = client.post("/ingest", json={"repo": "."})
    assert ingest.status_code == 200
    assert ingest.json()["indexed"] > 0

    response = client.post("/query", json={"question": "how does retrieval work", "top_k": 5})
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert all("path" in item and "score" in item for item in payload)


def test_answer_returns_grounded_structure() -> None:
    client = _client()
    client.post("/ingest", json={"repo": "."})
    response = client.post("/answer", json={"question": "what is the retriever", "top_k": 5})
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert "citations" in data
    assert "confidence" in data
    assert "grounded" in data


def test_query_matches_core_retriever_contract() -> None:
    client = _client()
    client.post("/ingest", json={"repo": "."})
    question = "how does retrieval work"
    api_paths = [item["path"] for item in client.post("/query", json={"question": question}).json()]
    retriever = build_retriever(
        SETTINGS, backend=SETTINGS.vector_store, repo=".", strategy="dense", top_k=5
    )
    core_paths = [r.chunk.path for r in retriever.retrieve(question)]
    assert api_paths == core_paths


def test_bad_input_returns_422() -> None:
    client = _client()
    response = client.post("/query", json={})  # missing required 'question'
    assert response.status_code == 422


def test_ingest_defaults_to_configured_scope() -> None:
    client = _client()
    ingest = client.post("/ingest", json={})  # repo omitted -> Settings.repo
    assert ingest.status_code == 200
    assert ingest.json()["indexed"] > 0


def test_ingest_rejects_repo_outside_configured_scope() -> None:
    client = _client()
    response = client.post("/ingest", json={"repo": "/tmp"})
    assert response.status_code == 400
    assert "scope" in response.json()["detail"]
