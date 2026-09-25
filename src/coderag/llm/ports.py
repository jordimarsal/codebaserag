from typing import Any, Protocol, runtime_checkable


# region EmbedderError
class EmbedderError(Exception):
    """Raised when an embedder cannot produce vectors."""


# region LlmClient
@runtime_checkable
class LlmClient(Protocol):
    def generate(self, prompt: str) -> str:
        """Return the model's raw completion for the given prompt."""
        ...

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Return a JSON object conforming to ``schema`` for the given prompt."""
        ...

    def model_name(self) -> str:
        """Identifier of the underlying model."""
        ...
