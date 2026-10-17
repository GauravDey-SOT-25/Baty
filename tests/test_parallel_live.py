"""Explicitly opt-in live Parallel checks; excluded from ordinary unit runs.

These checks make billable provider requests. Set both PARALLEL_API_KEY and
PARALLEL_LIVE_TESTS=1 only when you intend to spend account credits.
"""
from __future__ import annotations

import os
import unittest

from src.research.parallel_client import ParallelProvider


LIVE_ENABLED = os.environ.get("PARALLEL_LIVE_TESTS") == "1" and bool(
    os.environ.get("PARALLEL_API_KEY", "").strip()
)


@unittest.skipUnless(LIVE_ENABLED, "set PARALLEL_LIVE_TESTS=1 and PARALLEL_API_KEY to enable billable live checks")
class ParallelLiveIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = ParallelProvider()

    def test_search_returns_source_urls(self):
        result = self.provider.search(
            "Find the current official CISA guidance on vulnerability remediation.",
            search_queries=["CISA vulnerability remediation guidance"],
            max_results=2,
        )
        self.assertTrue(result.results, "live Search returned no results")
        self.assertTrue(all(item.url.startswith("https://") for item in result.results))

    def test_extract_returns_or_reports_public_cisa_page(self):
        result = self.provider.extract(
            ["https://www.cisa.gov/known-exploited-vulnerabilities-catalog"],
            objective="Identify the purpose of the catalog.",
        )
        self.assertTrue(result.results or result.errors)
        for item in result.results:
            self.assertEqual(item.url, "https://www.cisa.gov/known-exploited-vulnerabilities-catalog")

    def test_task_creation_and_status_retrieval(self):
        task = self.provider.create_research_task(
            "Summarize the current official CISA advice for prioritizing known exploited vulnerabilities.",
            processor="base",
        )
        self.assertTrue(task.provider_run_id)
        self.assertIn(task.status, {"pending", "running", "completed", "failed"})
        polled = self.provider.get_task_result(task)
        self.assertIn(polled.status, {"pending", "running", "completed", "failed", "cancelled"})


if __name__ == "__main__":
    unittest.main()
