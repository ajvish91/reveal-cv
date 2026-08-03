#!/usr/bin/env python3
"""
Run-folder contract for agent-portable CV tailoring.

This module defines the stable file layout, task ordering, prompt/response
rules, and validation helpers shared by the generic runner, provider adapters,
and manual/external-agent workflows.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cv_generation.apply_prompts import APPLY_PROMPTS_FILENAME

CONTRACT_NAME = "cv_generation.run_folder"
CONTRACT_VERSION = "1.0"

OPTIONAL_POST_STEPS: tuple[str, ...] = ("07_cover_letter",)

TASK_ORDER: tuple[str, ...] = (
    "01_jd_parser_task.json",
    "02_keyword_ranker_task.json",
    "03_track_selector_task.json",
    "04_bullet_tailor_task.json",
    "05_ats_checker_task.json",
    "06_assembler_task.json",
)

OUTPUT_ORDER: tuple[str, ...] = (
    "01_jd_parser_output.json",
    "02_keyword_ranker_output.json",
    "03_track_selector_output.json",
    "04_bullet_tailor_output.json",
    "05_ats_checker_output.json",
    "06_assembler_output.json",
)


def task_output_pairs() -> list[tuple[str, str]]:
    return list(zip(TASK_ORDER, OUTPUT_ORDER))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def required_top_level_keys(schema: Any) -> list[str]:
    if not isinstance(schema, dict):
        return []
    return [k for k in schema.keys() if isinstance(k, str)]


def parse_json_response(raw: str) -> dict[str, Any]:
    txt = raw.strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        if txt.startswith("json"):
            txt = txt[4:].strip()
    out = json.loads(txt)
    if not isinstance(out, dict):
        raise ValueError("Agent response is not a JSON object.")
    return out


def validate_output_against_task(task: dict[str, Any], output: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(output, dict):
        return ["Output must be a JSON object."]
    required = required_top_level_keys(task.get("expected_output_schema"))
    for key in required:
        if key not in output:
            errors.append(f"Missing top-level key: {key}")
    return errors


def manual_prompt_path(run_dir: Path, step_stem: str) -> Path:
    return run_dir / f"{step_stem}_prompt.txt"


def manual_response_path(run_dir: Path, step_stem: str) -> Path:
    return run_dir / f"{step_stem}_output.manual.json"


def contract_metadata() -> dict[str, Any]:
    return {
        "contract_name": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "task_order": list(TASK_ORDER),
        "output_order": list(OUTPUT_ORDER),
        "response_format": "strict_json_object",
        "deterministic_steps": ["06_assembler_task.json"],
        "optional_post_steps": list(OPTIONAL_POST_STEPS),
        "supplementary_generation": {
            "07_cover_letter": {
                "output_markdown": "cover_letter.md",
                "output_pdf": "cover_letter.pdf",
                "format": "markdown",
                "when": (
                    "detect_supplementary_artifacts flags cover_letter.md "
                    "and selected track is industry"
                ),
                "skipped_when": "cover_letter.md already exists (unless --overwrite)",
            }
        },
        "optional_files": [APPLY_PROMPTS_FILENAME],
    }


def write_contract_manifest(run_dir: Path) -> Path:
    path = run_dir / "agent_contract.json"
    write_json(path, contract_metadata())
    return path
