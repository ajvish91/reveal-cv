"""Central configuration for CV-generation agent providers.

Provider/model resolution lives here rather than in ``run_agent_pipeline`` so
the backend can be swapped (OpenRouter/Mistral, Cursor, Anthropic, OpenAI,
manual) by editing config or env vars instead of touching pipeline code.

Resolution order (first non-empty wins):

1. Explicit argument passed by the caller (CLI ``--provider`` / ``--model``).
2. ``CV_AGENT_PROVIDER`` / ``CV_AGENT_MODEL`` (highest-priority env override).
3. ``DEFAULT_LLM_PROVIDER`` / ``DEFAULT_LLM_MODEL`` (repo ``.env``).
4. Built-in default (OpenRouter + Mistral).
"""
from __future__ import annotations

import os

DEFAULT_PROVIDER = "openrouter"

# Fallback model per provider when nothing else is configured.
PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "openrouter": "mistralai/mistral-medium-3.1",
    "cursor": "composer-2.5",
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
    "manual": "manual",
}

_PROVIDER_ENV_VARS = ("CV_AGENT_PROVIDER", "DEFAULT_LLM_PROVIDER")
_MODEL_ENV_VARS = ("CV_AGENT_MODEL", "DEFAULT_LLM_MODEL")


def _first_env(names: tuple[str, ...]) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def env_provider() -> str:
    """Provider named by env vars, or the built-in default."""
    return (_first_env(_PROVIDER_ENV_VARS) or DEFAULT_PROVIDER).lower()


def resolve_provider(provider: str | None = None) -> str:
    """Resolve the active provider name."""
    resolved = (provider or "").strip() or _first_env(_PROVIDER_ENV_VARS) or DEFAULT_PROVIDER
    return resolved.lower()


def default_model_for(provider: str) -> str:
    """Built-in model id for a provider."""
    return PROVIDER_DEFAULT_MODELS.get(provider, PROVIDER_DEFAULT_MODELS[DEFAULT_PROVIDER])


def resolve_model(provider: str, model: str | None = None) -> str:
    """Resolve the model id for ``provider``.

    The env-configured default model only applies to the env-configured
    provider, so switching ``--provider`` does not inherit a mismatched model.
    """
    explicit = (model or "").strip()
    if explicit:
        return explicit
    if provider == env_provider():
        env_model = _first_env(_MODEL_ENV_VARS)
        if env_model:
            return env_model
    return default_model_for(provider)
