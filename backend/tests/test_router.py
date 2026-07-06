"""Unit tests for the router's defensive fallback logic (no API key needed)."""
import app.router.classifier as classifier
from app.router.classifier import classify_route


class _BoomLLM:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("no network / no key")


def test_fallback_when_classification_fails_with_documents(monkeypatch) -> None:
    monkeypatch.setattr(classifier, "ChatOpenAI", _BoomLLM)
    assert classify_route("anything", has_documents=True) == "unstructured"


def test_fallback_when_classification_fails_without_documents(monkeypatch) -> None:
    monkeypatch.setattr(classifier, "ChatOpenAI", _BoomLLM)
    assert classify_route("anything", has_documents=False) == "structured"


def test_invalid_route_word_falls_back(monkeypatch) -> None:
    class _BananaChain:
        def __init__(self, *a, **k):
            pass

        def __or__(self, other):
            return self

        def invoke(self, _):
            return "banana"

    # Make the whole prompt|llm|parser pipeline return an invalid route word.
    monkeypatch.setattr(classifier, "ChatOpenAI", lambda *a, **k: _BananaChain())
    monkeypatch.setattr(classifier, "ChatPromptTemplate", type("P", (), {
        "from_messages": staticmethod(lambda *_a, **_k: _BananaChain())
    }))
    assert classify_route("anything", has_documents=True) == "unstructured"
