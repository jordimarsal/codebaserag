import urllib.error
import urllib.request

from coderag.compose import build_embedder
from coderag.config import Settings
from coderag.llm.llamacpp_embedder import LlamaCppEmbedder
from coderag.llm.ollama_embedder import EmbedderError, OllamaEmbedder
from coderag.stores.ports import Embedder


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _fake_urlopen(payload: bytes | None = None):
    def _open(request, timeout=60):  # noqa: ANN001
        if payload is not None:
            return _FakeResponse(payload)
        import json as _json

        sent = _json.loads(request.data)
        texts = sent.get("input", [])
        data = [{"embedding": [float(i), 0.0, 0.0]} for i in range(len(texts))]
        return _FakeResponse(_json.dumps({"data": data}).encode())

    return _open


def test_llamacpp_embed_parses_openai_response(monkeypatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen())
    embedder = LlamaCppEmbedder(model="default", base_url="http://localhost:8080")
    vectors = embedder.embed(["a", "b"])
    assert len(vectors) == 2
    assert all(len(v) == 3 for v in vectors)
    assert embedder.dim() == 3


def test_llamacpp_embed_raises_on_mismatch(monkeypatch) -> None:
    body = b'{"data":[{"embedding":[0.1,0.2]}]}'
    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen(body))
    embedder = LlamaCppEmbedder()
    try:
        embedder.embed(["a", "b"])
        raise AssertionError("expected EmbedderError")
    except EmbedderError:
        pass


def test_llamacpp_embed_raises_on_url_error(monkeypatch) -> None:
    def _boom(request, timeout=60):  # noqa: ANN001
        raise urllib.error.URLError("down")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    embedder = LlamaCppEmbedder()
    try:
        embedder.embed(["a"])
        raise AssertionError("expected EmbedderError")
    except EmbedderError:
        pass


def test_build_embedder_selects_backend() -> None:
    settings = Settings(embedder_backend="llamacpp", embedder_url="http://localhost:8080")
    assert isinstance(build_embedder(settings), LlamaCppEmbedder)
    default = Settings(embedder_backend="ollama")
    assert isinstance(build_embedder(default), OllamaEmbedder)
    assert isinstance(build_embedder(Settings()), Embedder)
