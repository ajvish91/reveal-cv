"""./cv pdf must apply the same leftover-placeholder gate as deanonymize --strict."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.private_cv import (
    PrivateConfig,
    assert_cv_ready_for_pdf,
    run_render_pdf,
)


def _cfg(private: Path, mapping: Path) -> PrivateConfig:
    return PrivateConfig(
        repo_root=REPO,
        cv_package_dir=REPO / "cv_generation",
        private_dir=private,
        mapping_file=mapping,
        output_dir=private / "deanonymized",
        profile_photo=private / "missing.jpg",
    )


class TestPdfStrictGate(unittest.TestCase):
    def test_refuses_final_cv_with_leftover_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping = root / "cv_identity_mapping.json"
            mapping.write_text(
                json.dumps(
                    {
                        "ALEX RIVERA": "Jane Doe",
                        "Northline Labs": "REPLACE_WITH_EMPLOYER_1",
                    }
                ),
                encoding="utf-8",
            )
            md = root / "final_cv.md"
            md.write_text("# ALEX RIVERA\nStill has Northline Labs\n", encoding="utf-8")
            cfg = _cfg(root, mapping)
            code = assert_cv_ready_for_pdf(cfg, md)
            self.assertEqual(code, 4)

    def test_allows_clean_final_cv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping = root / "cv_identity_mapping.json"
            mapping.write_text(
                json.dumps({"ALEX RIVERA": "Jane Doe", "Northline Labs": "Acme"}),
                encoding="utf-8",
            )
            md = root / "final_cv.md"
            md.write_text("# Jane Doe\nWorked at Acme\n", encoding="utf-8")
            cfg = _cfg(root, mapping)
            self.assertEqual(assert_cv_ready_for_pdf(cfg, md), 0)

    def test_force_bypasses_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping = root / "cv_identity_mapping.json"
            mapping.write_text(
                json.dumps({"ALEX RIVERA": "Jane Doe"}),
                encoding="utf-8",
            )
            md = root / "final_cv.md"
            md.write_text("# ALEX RIVERA\n", encoding="utf-8")
            cfg = _cfg(root, mapping)
            self.assertEqual(assert_cv_ready_for_pdf(cfg, md, force=True), 0)

    def test_cover_letter_skips_strict_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping = root / "cv_identity_mapping.json"
            mapping.write_text(json.dumps({"ALEX RIVERA": "Jane Doe"}), encoding="utf-8")
            md = root / "cover_letter.md"
            md.write_text("Dear team\nALEX RIVERA\nSincerely\n", encoding="utf-8")
            cfg = _cfg(root, mapping)
            self.assertEqual(assert_cv_ready_for_pdf(cfg, md), 0)

    def test_identity_language_lines_do_not_block_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping = root / "cv_identity_mapping.json"
            mapping.write_text(
                json.dumps(
                    {
                        "ALEX RIVERA": "Jane Doe",
                        "- Hindi (Fluent)": "- Hindi (Fluent)",
                        "- Norwegian (B2, studying)": "- Norwegian (B2, studying)",
                    }
                ),
                encoding="utf-8",
            )
            md = root / "final_cv.md"
            md.write_text(
                "# Jane Doe\n## Languages\n- Hindi (Fluent)\n- Norwegian (B2, studying)\n",
                encoding="utf-8",
            )
            cfg = _cfg(root, mapping)
            self.assertEqual(assert_cv_ready_for_pdf(cfg, md), 0)

    def test_example_language_identity_still_blocks_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping = root / "cv_identity_mapping.json"
            mapping.write_text(
                json.dumps(
                    {
                        "ALEX RIVERA": "Jane Doe",
                        "- Example Language (Intermediate)": "- Example Language (Intermediate)",
                    }
                ),
                encoding="utf-8",
            )
            md = root / "final_cv.md"
            md.write_text(
                "# Jane Doe\n## Languages\n- Example Language (Intermediate)\n",
                encoding="utf-8",
            )
            cfg = _cfg(root, mapping)
            self.assertEqual(assert_cv_ready_for_pdf(cfg, md), 4)

    def test_run_render_pdf_does_not_call_renderer_when_strict_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping = root / "cv_identity_mapping.json"
            mapping.write_text(
                json.dumps({"ALEX RIVERA": "Jane Doe"}),
                encoding="utf-8",
            )
            md = root / "final_cv.md"
            md.write_text("# ALEX RIVERA\n", encoding="utf-8")
            cfg = _cfg(root, mapping)
            with patch("cv_generation.private_cv.subprocess.call") as call:
                code = run_render_pdf(cfg, md)
            self.assertEqual(code, 4)
            call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
