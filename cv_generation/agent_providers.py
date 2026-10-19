#!/usr/bin/env python3
"""
Pluggable LLM backends for CV subagent steps.

Providers:
  openrouter — OpenRouter gateway (default; needs requests + OPENROUTER_API_KEY)
  cursor     — Cursor SDK (needs cursor-sdk + CURSOR_API_KEY)
  anthropic  — Anthropic Messages API (needs anthropic + ANTHROPIC_API_KEY)
  openai     — OpenAI Chat Completions (needs openai + OPENAI_API_KEY)
  manual     — Write prompt to run_dir; read response from *_output.manual.json
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cv_generation.agent_config import default_model_for
from cv_generation.agent_contract import manual_prompt_path, manual_response_path


@dataclass
class AgentRunResult:
    text: str
    provider: str
    model: str
    run_id: str = ""
    tokens_input: int | None = None
    tokens_output: int | None = None
    duration_sec: float | None = None


class AgentProvider(ABC):
    name: str

    @abstractmethod
    def run(self, prompt: str, *, model: str, cwd: Path | None = None) -> AgentRunResult:
        ...

    def run_markdown(self, prompt: str, *, model: str, cwd: Path | None = None) -> AgentRunResult:
        """Like ``run()``, but without JSON-only response constraints."""
        return self.run(prompt, model=model, cwd=cwd)


class OpenRouterAgentProvider(AgentProvider):
    """OpenRouter (OpenAI-compatible gateway).

    Default backend, used here to reach Mistral models. Configure the API key
    with ``OPENROUTER_API_KEY`` and pick a model via ``--model`` or
    ``CV_AGENT_MODEL`` / ``DEFAULT_LLM_MODEL``.
    """

    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1/chat/completions"
    referer = "https://github.com/anomalyco/job-search-automation"

    def _complete(self, prompt: str, *, model: str, json_only: bool) -> AgentRunResult:
        try:
            import requests
        except ImportError as err:
            raise RuntimeError("openrouter provider requires: pip install requests") from err

        import os
        import time

        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set.")

        model_id = model or default_model_for(self.name)
        payload: dict[str, Any] = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 8192,
        }

        started = time.monotonic()
        try:
            resp = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self.referer,
                    "X-Title": "Job Search CV Tailoring",
                },
                json=payload,
                timeout=180,
            )
            resp.raise_for_status()
        except Exception as err:  # noqa: BLE001 - surface any transport/HTTP error
            raise RuntimeError(f"OpenRouter request failed: {err}") from err

        try:
            data = resp.json()
        except ValueError as err:
            raise RuntimeError("OpenRouter returned non-JSON response.") from err

        choices = data.get("choices") or []
        message = (choices[0].get("message") or {}) if choices else {}
        text = (message.get("content") or "").strip()
        if not text:
            raise RuntimeError("OpenRouter returned empty response.")

        usage = data.get("usage") or {}
        return AgentRunResult(
            text=text,
            provider=self.name,
            model=data.get("model") or model_id,
            duration_sec=round(time.monotonic() - started, 3),
            tokens_input=usage.get("prompt_tokens"),
            tokens_output=usage.get("completion_tokens"),
        )

    def run(self, prompt: str, *, model: str, cwd: Path | None = None) -> AgentRunResult:
        return self._complete(prompt, model=model, json_only=True)

    def run_markdown(self, prompt: str, *, model: str, cwd: Path | None = None) -> AgentRunResult:
        return self._complete(prompt, model=model, json_only=False)


class CursorAgentProvider(AgentProvider):
    name = "cursor"

    def run(self, prompt: str, *, model: str, cwd: Path | None = None) -> AgentRunResult:
        try:
            from cursor_sdk import Agent, AgentOptions, CursorAgentError, LocalAgentOptions
        except ImportError as err:
            raise RuntimeError(
                "cursor provider requires: pip install cursor-sdk"
            ) from err

        import os

        api_key = os.environ.get("CURSOR_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("CURSOR_API_KEY is not set.")

        options = AgentOptions(
            api_key=api_key,
            model=model,
            local=LocalAgentOptions(cwd=str(cwd or Path.cwd())),
        )
        try:
            result = Agent.prompt(prompt, options)
        except CursorAgentError as err:
            raise RuntimeError(f"Cursor agent error: {err}") from err

        if result.status == "error":
            raise RuntimeError(f"Cursor run failed, run_id={result.id}")

        text = (result.result or "").strip()
        if not text:
            raise RuntimeError("Cursor returned empty response.")
        duration_sec = (result.duration_ms / 1000.0) if result.duration_ms else None
        return AgentRunResult(
            text=text,
            provider=self.name,
            model=model,
            run_id=result.id or "",
            duration_sec=duration_sec,
        )


class AnthropicAgentProvider(AgentProvider):
    name = "anthropic"

    def run(self, prompt: str, *, model: str, cwd: Path | None = None) -> AgentRunResult:
        try:
            import anthropic
        except ImportError as err:
            raise RuntimeError("anthropic provider requires: pip install anthropic") from err

        import os

        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "").strip())
        if not client.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")

        model_id = model if model.startswith("claude") else "claude-sonnet-4-20250514"
        msg = client.messages.create(
            model=model_id,
            max_tokens=8192,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                    + "\n\nReply with valid JSON only (no markdown fences unless JSON is inside).",
                }
            ],
        )
        parts = []
        for block in msg.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        text = "\n".join(parts).strip()
        if not text:
            raise RuntimeError("Anthropic returned empty response.")
        usage = getattr(msg, "usage", None)
        tokens_in = getattr(usage, "input_tokens", None) if usage else None
        tokens_out = getattr(usage, "output_tokens", None) if usage else None
        return AgentRunResult(
            text=text,
            provider=self.name,
            model=model_id,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
        )

    def run_markdown(self, prompt: str, *, model: str, cwd: Path | None = None) -> AgentRunResult:
        try:
            import anthropic
        except ImportError as err:
            raise RuntimeError("anthropic provider requires: pip install anthropic") from err

        import os

        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "").strip())
        if not client.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")

        model_id = model if model.startswith("claude") else "claude-sonnet-4-20250514"
        msg = client.messages.create(
            model=model_id,
            max_tokens=8192,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                    + "\n\nReply with the cover letter markdown only (no JSON, no code fences).",
                }
            ],
        )
        parts = []
        for block in msg.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        text = "\n".join(parts).strip()
        if not text:
            raise RuntimeError("Anthropic returned empty response.")
        usage = getattr(msg, "usage", None)
        tokens_in = getattr(usage, "input_tokens", None) if usage else None
        tokens_out = getattr(usage, "output_tokens", None) if usage else None
        return AgentRunResult(
            text=text,
            provider=self.name,
            model=model_id,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
        )


class OpenAIAgentProvider(AgentProvider):
    name = "openai"

    def run(self, prompt: str, *, model: str, cwd: Path | None = None) -> AgentRunResult:
        try:
            from openai import OpenAI
        except ImportError as err:
            raise RuntimeError("openai provider requires: pip install openai") from err

        import os

        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        model_id = model if model else "gpt-4o"
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": "You are a CV tailoring assistant. Output valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            raise RuntimeError("OpenAI returned empty response.")
        usage = getattr(resp, "usage", None)
        tokens_in = getattr(usage, "prompt_tokens", None) if usage else None
        tokens_out = getattr(usage, "completion_tokens", None) if usage else None
        return AgentRunResult(
            text=text,
            provider=self.name,
            model=model_id,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
        )

    def run_markdown(self, prompt: str, *, model: str, cwd: Path | None = None) -> AgentRunResult:
        try:
            from openai import OpenAI
        except ImportError as err:
            raise RuntimeError("openai provider requires: pip install openai") from err

        import os

        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        model_id = model if model else "gpt-4o"
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": "You write tailored cover letters. Output markdown only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            raise RuntimeError("OpenAI returned empty response.")
        usage = getattr(resp, "usage", None)
        tokens_in = getattr(usage, "prompt_tokens", None) if usage else None
        tokens_out = getattr(usage, "completion_tokens", None) if usage else None
        return AgentRunResult(
            text=text,
            provider=self.name,
            model=model_id,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
        )


class ManualAgentProvider(AgentProvider):
    """Write prompt; user pastes JSON into the manual response file in run_dir."""

    name = "manual"

    def __init__(self, run_dir: Path, step_stem: str) -> None:
        self.run_dir = run_dir
        self.step_stem = step_stem

    def run(self, prompt: str, *, model: str, cwd: Path | None = None) -> AgentRunResult:
        prompt_path = manual_prompt_path(self.run_dir, self.step_stem)
        out_path = manual_response_path(self.run_dir, self.step_stem)
        prompt_path.write_text(prompt, encoding="utf-8")
        if not out_path.is_file():
            raise RuntimeError(
                "Manual mode requires an external agent step.\n"
                f"1. Open the prompt file:\n  {prompt_path}\n"
                f"2. Run it with Claude/Codex/another agent.\n"
                f"3. Save the strict JSON response to:\n  {out_path}"
            )
        text = out_path.read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeError(f"Manual response file is empty: {out_path}")
        return AgentRunResult(text=text, provider=self.name, model=model or "manual")


def get_provider(name: str, *, run_dir: Path | None = None, step_stem: str = "") -> AgentProvider:
    key = (name or "openrouter").strip().lower()
    if key == "openrouter":
        return OpenRouterAgentProvider()
    if key == "cursor":
        return CursorAgentProvider()
    if key == "anthropic":
        return AnthropicAgentProvider()
    if key == "openai":
        return OpenAIAgentProvider()
    if key == "manual":
        if run_dir is None or not step_stem:
            raise ValueError("manual provider requires run_dir and step_stem")
        return ManualAgentProvider(run_dir, step_stem)
    raise ValueError(
        f"Unknown agent provider: {name!r}. Use: openrouter, cursor, anthropic, openai, manual."
    )


def call_markdown_agent(
    prompt: str,
    *,
    run_dir: Path,
    step_stem: str,
    provider_name: str,
    model: str,
) -> AgentRunResult:
    """
    Run a markdown-producing agent step (cover letter, application letter, etc.).

    Manual mode uses ``{step_stem}_prompt.txt`` / ``{step_stem}_output.manual.md``
    (not the JSON manual paths used by pipeline subagents).
    """
    if provider_name == "manual":
        prompt_path = run_dir / f"{step_stem}_prompt.txt"
        response_path = run_dir / f"{step_stem}_output.manual.md"
        prompt_path.write_text(prompt, encoding="utf-8")
        if not response_path.is_file():
            raise RuntimeError(
                "Manual mode requires an external agent step.\n"
                f"1. Open the prompt file:\n  {prompt_path}\n"
                f"2. Run it with Claude/Codex/another agent.\n"
                f"3. Save the markdown to:\n  {response_path}"
            )
        text = response_path.read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeError(f"Manual response file is empty: {response_path}")
        return AgentRunResult(text=text, provider="manual", model=model or "manual")

    backend = get_provider(provider_name)
    return backend.run_markdown(prompt, model=model, cwd=Path.cwd())


def list_providers() -> list[str]:
    return ["openrouter", "cursor", "anthropic", "openai", "manual"]
