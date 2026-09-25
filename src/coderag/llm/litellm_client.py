import json
import logging
from typing import Any

logger = logging.getLogger("coderag.llm")


# region LitellmClient
class LitellmClient:
    def __init__(self, model: str = "gpt-4o-mini", backend: str = "litellm") -> None:
        from litellm import completion  # lazy: optional dependency

        self._model = model
        self._backend = backend
        self._completion = completion

    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: str) -> str:
        response = self._completion(
            model=self._model, messages=[{"role": "user", "content": prompt}]
        )
        return str(response.choices[0].message.content or "")

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        response = self._completion(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "answer", "schema": schema},
            },
        )
        content = str(response.choices[0].message.content or "")
        try:
            payload: dict[str, Any] = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM did not return valid JSON: {exc}") from exc
        return payload
