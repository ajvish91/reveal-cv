"""Tests for job_search.logging_config."""
from __future__ import annotations

import logging
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from job_search.logging_config import (
    configure_logging,
    get_logger,
    log_json_summary,
    tail_log_file,
)


class LoggingConfigTests(unittest.TestCase):
    def test_configure_logging_writes_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "job_search.log"
            configure_logging(level=logging.DEBUG, log_file=log_path, console=False)
            logger = get_logger("job_search.ingest_nav")
            logger.info("nav ingest test line")
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("nav ingest test line", text)
            self.assertIn("job_search.ingest_nav", text)

    def test_log_json_summary_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "summary.log"
            configure_logging(log_file=log_path, console=False)
            logger = get_logger("job_search.ingest_finn")
            log_json_summary(logger, "FINN ingest summary", {"stored_rows": 3, "queries": ["postdoc"]})
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("FINN ingest summary", text)
            self.assertIn("stored_rows", text)

    def test_tail_log_file_returns_last_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "tail.log"
            lines = [f"line-{i}" for i in range(60)]
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            tail = tail_log_file(log_path, lines=50)
            self.assertIn("line-59", tail)
            self.assertNotIn("line-0", tail)


if __name__ == "__main__":
    unittest.main()
