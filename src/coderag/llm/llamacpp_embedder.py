import contextlib
import json
import urllib.error
import urllib.request

from coderag.llm.ollama_embedder import EmbedderError


# region LlamaCppEmbedder
class LlamaCppEmbedder:
    def __init__(
        self,
        model: str = "default",
        base_url: str = "http://localhost:8080",
        batch_size: int = 32,
        max_chars: int = 4000,
    ) -> None:
        self._model = model
        self._url = base_url.rstrip("/") + "/v1/embeddings"
        self._batch_size = batch_size
        self._max_chars = max_chars
        self._dim: int | None = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            try:
                embeddings.extend(self._embed_batch(batch, self._max_chars))
            except EmbedderError as exc:
                if "500" in str(exc) and self._max_chars > 256:
                    embeddings.extend(self._embed_batch(batch, self._max_chars // 2))
                else:
                    raise
        return embeddings

    def _embed_batch(self, batch: list[str], max_chars: int) -> list[list[float]]:
        payload = json.dumps(
            {"input": [t[:max_chars] for t in batch], "model": self._model}
        ).encode("utf-8")
        request = urllib.request.Request(
            self._url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = ""
            with contextlib.suppress(OSError):
                detail = exc.read().decode("utf-8", "ignore")
            raise EmbedderError(f"llama.cpp embeddings request failed: {exc} {detail}") from exc
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise EmbedderError(f"llama.cpp embeddings request failed: {exc}") from exc
        vectors = [item["embedding"] for item in data["data"]]
        if len(vectors) != len(batch):
            raise EmbedderError("llama.cpp returned a different number of vectors than texts")
        return vectors

    def dim(self) -> int:
        if self._dim is None:
            self._dim = len(self.embed(["__dim_probe__"])[0])
        return self._dim
