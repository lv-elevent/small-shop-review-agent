"""LLM Router — unified provider selection with env-var support. No provider logic here."""
from __future__ import annotations

import os
from dataclasses import dataclass

from small_shop_agent.llm.base import BaseLLMProvider

_SUPPORTED_MODES = ("demo", "mock", "live", "openai", "ollama")


@dataclass
class LLMRouterConfig:
    """Resolved router configuration."""
    mode: str
    provider_name: str
    model: str | None = None
    base_url: str | None = None


def _build_config(mode: str, provider_name: str) -> LLMRouterConfig:
    return LLMRouterConfig(
        mode=mode,
        provider_name=provider_name,
        model=os.environ.get("OPENAI_MODEL"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )


def _resolve_mode(mode: str | None) -> str:
    if mode is not None:
        return mode.lower().strip()
    return os.environ.get("LLM_MODE", "demo").lower().strip()


def get_llm_provider(mode: str | None = None, model_name: str | None = None) -> BaseLLMProvider:
    """Return a BaseLLMProvider instance based on mode.

    Args:
        mode: One of "demo", "mock", "live", "openai".
              If None, reads LLM_MODE env var; defaults to "demo".
        model_name: Optional model override for multi-agent scenarios.

    Returns:
        A BaseLLMProvider instance.

    Raises:
        ValueError: Unknown mode.
        NotImplementedError: Ollama mode (not in v0.6).
        RuntimeError: Missing OPENAI_API_KEY or unavailable provider.
    """
    resolved = _resolve_mode(mode)

    # ── Demo / Mock ──
    if resolved in ("demo", "mock"):
        from small_shop_agent.demo.demo_loader import DemoLoader
        from small_shop_agent.llm.mock_provider import MockProvider
        return MockProvider(DemoLoader())

    # ── Ollama ──
    if resolved == "ollama":
        from small_shop_agent.llm.ollama_provider import OllamaProvider
        return OllamaProvider()

    # ── Live / OpenAI ──
    if resolved in ("live", "openai"):
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY environment variable is not set. "
                "Set it via: export OPENAI_API_KEY=sk-... "
                "or switch to demo mode: export LLM_MODE=demo"
            )

        try:
            from small_shop_agent.llm.openai_provider import OpenAIProvider  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI provider module is not available. "
                "Ensure openai_provider.py is implemented and the openai package is installed."
            ) from exc

        return OpenAIProvider(api_key=api_key, model=model_name or os.environ.get("OPENAI_MODEL"))

    # ── Unknown ──
    raise ValueError(
        f"Unknown LLM mode: {resolved!r}. "
        f"Supported modes: {', '.join(_SUPPORTED_MODES)}"
    )
