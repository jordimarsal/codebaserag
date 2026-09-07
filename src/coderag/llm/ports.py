from typing import Protocol, runtime_checkable


# region LlmClient
@runtime_checkable
class LlmClient(Protocol):
    def generate(self, prompt: str) -> str:
        """Return the model's raw completion for the given prompt."""
        ...

    def generate_structured(self, prompt: str, schema: dict) -> dict:
        """Return a JSON object conforming to ``schema`` for the given prompt."""
        ...

    def model_name(self) -> str:
        """Identifier of the underlying model."""
        ...
