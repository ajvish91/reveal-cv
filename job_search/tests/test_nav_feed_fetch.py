from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from job_search.ingest_nav_jobs import fetch_nav_feed_page


class NavFeedFetchTests(unittest.TestCase):
    def test_retries_without_conditional_headers_on_504(self) -> None:
        client = MagicMock()
        client.fetch_feed_page.side_effect = [
            RuntimeError("HTTP 504 https://pam-stilling-feed.nav.no/api/v1/feed: gateway"),
            ({"items": [{"id": "1"}]}, {"etag": "new"}),
        ]
        ims = datetime(2026, 10, 10, tzinfo=timezone.utc)
        page, hdrs = fetch_nav_feed_page(
            client,
            "/api/v1/feed",
            page_num=1,
            if_modified_since=ims,
            etag="old-etag",
        )
        self.assertEqual(len(page["items"]), 1)
        self.assertEqual(client.fetch_feed_page.call_count, 2)
        client.fetch_feed_page.assert_any_call("/api/v1/feed")

    def test_does_not_retry_when_unconditional_fails(self) -> None:
        client = MagicMock()
        client.fetch_feed_page.side_effect = RuntimeError("HTTP 500")
        with self.assertRaises(RuntimeError):
            fetch_nav_feed_page(
                client,
                "/api/v1/feed",
                page_num=1,
                if_modified_since=None,
                etag=None,
            )
        self.assertEqual(client.fetch_feed_page.call_count, 1)


if __name__ == "__main__":
    unittest.main()
