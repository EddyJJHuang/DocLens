"""Model registry for the multi-LLM eval.

Builds a provider-agnostic LangChain chat model per spec. Providers whose API key
is not configured are skipped. Model list is read from the EVAL_MODELS env var
(comma-separated "provider:model_id"), else a sensible default.
"""
import logging
import os
from dataclasses import dataclass
from typing import List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Cheap-but-capable defaults. claude-haiku-4-5 is used (not the newer Claude
# models) because it still accepts a temperature parameter and is the cheapest.
DEFAULT_MODELS = [
    "openai:gpt-4o-mini",
    "openai:gpt-4o",
    "anthropic:claude-haiku-4-5",
    "google:gemini-2.5-flash",
]

MAX_TOKENS = 1024


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model_id: str

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model_id}"


def _key_for(provider: str) -> str:
    return {
        "openai": settings.openai_api_key,
        "anthropic": settings.anthropic_api_key,
        "google": settings.google_api_key,
    }.get(provider, "")


def parse_specs() -> List[ModelSpec]:
    raw = os.environ.get("EVAL_MODELS", "").strip()
    entries = [e.strip() for e in raw.split(",") if e.strip()] if raw else DEFAULT_MODELS
    specs = []
    for entry in entries:
        provider, _, model_id = entry.partition(":")
        if provider and model_id:
            specs.append(ModelSpec(provider.strip(), model_id.strip()))
    return specs


def build_model(spec: ModelSpec):
    """Construct a LangChain chat model for the spec, or None if unavailable."""
    key = _key_for(spec.provider)
    if not key or key == "your_openai_api_key_here":
        logger.info("Skipping %s — no API key configured.", spec.label)
        return None
    try:
        if spec.provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=spec.model_id, temperature=0, api_key=key, max_tokens=MAX_TOKENS, timeout=90)
        if spec.provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            # No temperature: newer Claude models reject sampling params (haiku accepts it, but omit for portability).
            return ChatAnthropic(model=spec.model_id, api_key=key, max_tokens=MAX_TOKENS, timeout=90)
        if spec.provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model=spec.model_id, google_api_key=key, temperature=0, max_output_tokens=MAX_TOKENS)
    except Exception as exc:
        logger.warning("Could not build %s: %s", spec.label, exc)
        return None
    logger.warning("Unknown provider: %s", spec.provider)
    return None


def available_models() -> List[tuple]:
    """Return [(ModelSpec, model)] for every spec whose provider is configured and builds."""
    built = []
    for spec in parse_specs():
        model = build_model(spec)
        if model is not None:
            built.append((spec, model))
    return built
