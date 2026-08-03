#!/usr/bin/env python3
"""
Collect per-run pipeline timing, token usage, and rough energy estimates.

Written to ``pipeline_metrics.json`` in each ``cv_runs/<run_id>/`` folder after
``run_agent_pipeline`` completes. See ``PIPELINE_IMPACT.md`` for limitations.
"""
from __future__ import annotations

import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

METRICS_VERSION = 1
METRICS_FILENAME = "pipeline_metrics.json"

# Rough inference energy: ~0.5 Wh per 1k tokens (mid-range cloud GPU inference).
# See PIPELINE_IMPACT.md for sources and caveats.
KWH_PER_1K_TOKENS = 0.0005
# Global average grid intensity (very approximate; datacenter PUE not modeled).
KG_CO2_PER_KWH = 0.4
CHARS_PER_TOKEN_ESTIMATE = 4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def peak_rss_mb() -> float | None:
    """Peak RSS of the current process (stdlib only; platform-specific units)."""
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss = float(usage.ru_maxrss)
        if sys.platform == "darwin":
            return round(rss / (1024 * 1024), 2)
        return round(rss / 1024, 2)
    except Exception:
        return None


def estimate_tokens_from_text(text: str) -> int:
    cleaned = (text or "").strip()
    if not cleaned:
        return 0
    return max(1, len(cleaned) // CHARS_PER_TOKEN_ESTIMATE)


TokenSource = Literal["api", "estimated_chars", "none"]


@dataclass
class StageMetrics:
    name: str
    started_at: str
    ended_at: str
    duration_sec: float
    provider: str = ""
    model: str = ""
    kind: str = "agent"
    skipped: bool = False
    tokens_input: int | None = None
    tokens_output: int | None = None
    tokens_source: TokenSource = "none"
    agent_run_id: str = ""
    prompt_chars: int = 0
    response_chars: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineMetrics:
    version: int = METRICS_VERSION
    started_at: str = ""
    ended_at: str = ""
    duration_sec: float = 0.0
    provider_default: str = ""
    model_default: str = ""
    stages: list[StageMetrics] = field(default_factory=list)
    peak_rss_mb: float | None = None
    totals: dict[str, Any] = field(default_factory=dict)
    energy_estimate: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_sec": round(self.duration_sec, 3),
            "provider_default": self.provider_default,
            "model_default": self.model_default,
            "stages": [s.to_dict() for s in self.stages],
            "process": {
                "peak_rss_mb": self.peak_rss_mb,
                "measured": self.peak_rss_mb is not None,
            },
            "totals": self.totals,
            "energy_estimate": self.energy_estimate,
        }


class PipelineMetricsCollector:
    """Accumulate stage metrics for one pipeline run."""

    def __init__(self, *, provider: str, model: str) -> None:
        self._provider = provider
        self._model = model
        self._started_mono = time.monotonic()
        self._started_at = utc_now_iso()
        self._stages: list[StageMetrics] = []
        self._peak_rss = peak_rss_mb()

    def record_stage(
        self,
        *,
        name: str,
        started_mono: float,
        ended_mono: float,
        provider: str = "",
        model: str = "",
        kind: str = "agent",
        skipped: bool = False,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        tokens_source: TokenSource = "none",
        agent_run_id: str = "",
        prompt_text: str = "",
        response_text: str = "",
    ) -> None:
        duration = max(0.0, ended_mono - started_mono)
        started_at = utc_now_iso()
        ended_at = utc_now_iso()
        in_tok = tokens_input
        out_tok = tokens_output
        source = tokens_source
        if in_tok is None and out_tok is None and not skipped:
            est_in = estimate_tokens_from_text(prompt_text)
            est_out = estimate_tokens_from_text(response_text)
            if est_in or est_out:
                in_tok = est_in
                out_tok = est_out
                source = "estimated_chars"
        rss = peak_rss_mb()
        if rss is not None and (self._peak_rss is None or rss > self._peak_rss):
            self._peak_rss = rss
        self._stages.append(
            StageMetrics(
                name=name,
                started_at=started_at,
                ended_at=ended_at,
                duration_sec=round(duration, 3),
                provider=provider or self._provider,
                model=model or self._model,
                kind=kind,
                skipped=skipped,
                tokens_input=in_tok,
                tokens_output=out_tok,
                tokens_source=source,
                agent_run_id=agent_run_id,
                prompt_chars=len(prompt_text or ""),
                response_chars=len(response_text or ""),
            )
        )

    def finalize(self) -> PipelineMetrics:
        ended_mono = time.monotonic()
        ended_at = utc_now_iso()
        duration_sec = ended_mono - self._started_mono

        tokens_in = 0
        tokens_out = 0
        has_api = False
        has_estimated = False
        for stage in self._stages:
            if stage.skipped:
                continue
            if stage.tokens_input is not None:
                tokens_in += stage.tokens_input
            if stage.tokens_output is not None:
                tokens_out += stage.tokens_output
            if stage.tokens_source == "api":
                has_api = True
            elif stage.tokens_source == "estimated_chars":
                has_estimated = True

        tokens_total = tokens_in + tokens_out
        energy = estimate_energy_kwh(tokens_in, tokens_out)

        if has_api and has_estimated:
            token_note = "mixed"
        elif has_api:
            token_note = "measured_api"
        elif has_estimated:
            token_note = "estimated_chars"
        else:
            token_note = "none"

        metrics = PipelineMetrics(
            started_at=self._started_at,
            ended_at=ended_at,
            duration_sec=round(duration_sec, 3),
            provider_default=self._provider,
            model_default=self._model,
            stages=list(self._stages),
            peak_rss_mb=self._peak_rss,
            totals={
                "wall_clock_sec": round(duration_sec, 3),
                "agent_steps": sum(1 for s in self._stages if s.kind == "agent" and not s.skipped),
                "tokens_input": tokens_in,
                "tokens_output": tokens_out,
                "tokens_total": tokens_total,
                "tokens_source": token_note,
            },
            energy_estimate=energy,
        )
        return metrics


def estimate_energy_kwh(tokens_input: int, tokens_output: int) -> dict[str, Any]:
    """Rough kWh / CO2 from token counts; not datacenter-specific."""
    total = max(0, tokens_input) + max(0, tokens_output)
    if total <= 0:
        return {
            "kwh": None,
            "co2_kg": None,
            "method": "token_based_v1",
            "disclaimer": (
                "No token counts available; energy not estimated. "
                "See PIPELINE_IMPACT.md."
            ),
        }
    kwh = (total / 1000.0) * KWH_PER_1K_TOKENS
    co2_kg = kwh * KG_CO2_PER_KWH
    return {
        "kwh": round(kwh, 5),
        "co2_kg": round(co2_kg, 5),
        "method": "token_based_v1",
        "constants": {
            "kwh_per_1k_tokens": KWH_PER_1K_TOKENS,
            "kg_co2_per_kwh": KG_CO2_PER_KWH,
        },
        "disclaimer": (
            "Approximate order-of-magnitude only. Assumes cloud GPU inference, "
            "does not model datacenter PUE, region grid mix, or Cursor agent "
            "tool-use overhead. Not suitable for carbon accounting."
        ),
    }


def write_pipeline_metrics(run_dir: Path, metrics: PipelineMetrics) -> Path:
    path = run_dir / METRICS_FILENAME
    path.write_text(
        json_dumps(metrics.to_dict()) + "\n",
        encoding="utf-8",
    )
    return path


def json_dumps(obj: dict[str, Any]) -> str:
    import json

    return json.dumps(obj, indent=2, ensure_ascii=False)


def load_pipeline_metrics(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / METRICS_FILENAME
    if not path.is_file():
        return None
    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def resolve_run_dir(run_id: str, *, repo_root: Path | None = None) -> Path | None:
    """Resolve a run basename to ``cv_generation/cv_runs/<run_id>``."""
    root = repo_root or Path(__file__).resolve().parents[1]
    run_dir = root / "cv_generation" / "cv_runs" / run_id.strip()
    return run_dir if run_dir.is_dir() else None


def format_duration_sec(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "—"
    total = int(round(seconds))
    if total < 60:
        return f"{total}s"
    minutes, secs = divmod(total, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def format_token_count(count: int | None) -> str:
    if count is None or count <= 0:
        return "—"
    if count >= 1_000_000:
        return f"~{count / 1_000_000:.1f}M"
    if count >= 1000:
        return f"~{count // 1000}k"
    return f"~{count}"


def format_pipeline_metrics_summary(metrics: dict[str, Any] | None) -> str | None:
    """Compact one-line summary for dashboard display."""
    if not metrics:
        return None
    totals = metrics.get("totals") or {}
    energy = metrics.get("energy_estimate") or {}
    duration = totals.get("wall_clock_sec") or metrics.get("duration_sec")
    tokens = totals.get("tokens_total")
    token_src = totals.get("tokens_source") or "none"
    parts: list[str] = []
    if duration is not None:
        parts.append(f"Pipeline: {format_duration_sec(float(duration))}")
    if tokens:
        prefix = "~" if token_src not in ("measured_api",) else ""
        if tokens >= 1000:
            parts.append(f"{prefix}{tokens // 1000}k tokens")
        else:
            parts.append(f"{prefix}{tokens} tokens")
    kwh = energy.get("kwh")
    if kwh is not None:
        parts.append(f"est. {kwh:.3f} kWh (approx.)")
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return " · ".join(parts)
