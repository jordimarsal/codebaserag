from coderag.llm.fake import FakeLlmClient
from coderag.llm.litellm_client import LitellmClient
from coderag.llm.ports import LlmClient


def test_fake_llm_conforms_to_port() -> None:
    assert isinstance(FakeLlmClient(), LlmClient)


def test_fake_llm_generate_returns_json() -> None:
    fake = FakeLlmClient({"q": {"answer": "x", "citations": []}})
    assert fake.generate("q") == '{"answer": "x", "citations": []}'
    assert fake.generate_structured("q", {}) == {"answer": "x", "citations": []}


def test_litellm_client_conforms_when_available() -> None:
    try:
        import litellm  # noqa: F401
    except ImportError:
        import pytest

        pytest.skip("litellm not installed")
    assert isinstance(LitellmClient(), LlmClient)
