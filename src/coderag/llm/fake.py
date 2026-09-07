import json

from coderag.llm.ports import LlmClient

# region FakeLlmClient
class FakeLlmClient:
    def __init__(
        self,
        answers: "dict[str, dict] | None" = None,
        default: "dict | None" = None,
        model: str = "fake",
    ) -> None:
        self._answers = answers or {}
        self._default = default or {"answer": "fake", "citations": [], "confidence": 0.5}
        self._model = model

    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: str) -> str:
        return json.dumps(self._answers.get(prompt, self._default))

    def generate_structured(self, prompt: str, schema: dict) -> dict:
        if prompt in self._answers:
            return self._answers[prompt]
        for key, value in self._answers.items():
            if key in prompt:
                return value
        return self._default

    @staticmethod
    def grounded_answer(paths: list[str]) -> dict:
        return {
            "answer": f"See {', '.join(paths)}.",
            "citations": [
                {"path": path, "line_start": 1, "line_end": 2} for path in paths
            ],
            "confidence": 0.9,
        }

    @staticmethod
    def ungrounded_answer() -> dict:
        return {
            "answer": "See elsewhere.",
            "citations": [{"path": "ghost.py", "line_start": 1, "line_end": 2}],
            "confidence": 0.9,
        }
