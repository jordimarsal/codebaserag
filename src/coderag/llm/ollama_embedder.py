from coderag.llm.ports import EmbedderError

__all__ = ["EmbedderError", "OllamaEmbedder"]


# region OllamaEmbedder
class OllamaEmbedder:
    def __init__(
        self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434"
    ) -> None:
        from ollama import Client  # lazy: optional dependency (embeddings extra)

        self._model = model
        self._client = Client(host=base_url.rstrip("/"))

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = self._client.embed(model=self._model, input=texts)
        except Exception as exc:
            raise EmbedderError(f"ollama embed failed: {exc}") from exc
        vectors = [list(vector) for vector in response["embeddings"]]
        return vectors

    def dim(self) -> int:
        probe = self.embed(["dimension-probe"])
        return len(probe[0])
