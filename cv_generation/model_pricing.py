"""Approximate model pricing (USD per 1K tokens) for cost estimates.

Values are rough OpenRouter/provider list prices captured for the models this
pipeline is likely to use. They drift over time; update when rates change and
treat any derived cost as an order-of-magnitude estimate only.
"""
from __future__ import annotations

MODEL_PRICING: dict[str, dict[str, float]] = {
    # Mistral via OpenRouter (USD per 1K tokens)
    "mistralai/mistral-small-3.2-24b-instruct": {"input": 0.00009375, "output": 0.00025},
    "mistralai/mistral-small-3.1-24b-instruct": {"input": 0.000351, "output": 0.000555},
    "mistralai/mistral-small-24b-instruct-2501": {"input": 0.00005, "output": 0.00008},
    "mistralai/mistral-nemo": {"input": 0.000029, "output": 0.00003},
    "mistralai/mistral-medium-3.1": {"input": 0.0004, "output": 0.002},
    "mistralai/mistral-medium-3": {"input": 0.0004, "output": 0.002},
    "mistralai/mistral-large-2512": {"input": 0.0005, "output": 0.0015},
    "mistralai/mistral-large": {"input": 0.002, "output": 0.006},
    "mistralai/devstral-2512": {"input": 0.0004, "output": 0.002},
    "mistralai/mistral-small-2603": {"input": 0.00015, "output": 0.0006},
    # Other providers
    "composer-2.5": {"input": 0.002, "output": 0.002},
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "gpt-4o": {"input": 0.005, "output": 0.015},
}


def estimate_cost_usd(
    model: str | None,
    tokens_input: int | None,
    tokens_output: int | None,
) -> float | None:
    """Estimate USD cost from token counts; ``None`` when not computable."""
    if not model or tokens_input is None or tokens_output is None:
        return None
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        return None
    input_cost = (tokens_input / 1000.0) * pricing["input"]
    output_cost = (tokens_output / 1000.0) * pricing["output"]
    return round(input_cost + output_cost, 6)
