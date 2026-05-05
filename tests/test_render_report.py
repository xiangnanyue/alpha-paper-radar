import unittest

from alpha_paper_radar.render_report import render_markdown_report


class TestRenderReport(unittest.TestCase):
    def test_render_markdown_report_contains_sections(self):
        sections = {
            "new": [
                {
                    "canonical_id": "1234.5678",
                    "title": "Agent Transformer for Portfolio Optimization",
                    "authors": ["Alice", "Bob"],
                    "published": "2026-05-01T00:00:00Z",
                    "updated": "2026-05-01T00:00:00Z",
                    "latest_version": 2,
                    "priority": "unscored",
                    "topics": ["quant_finance", "llm_progress"],
                }
            ],
            "updated": [],
            "carryover": [],
        }
        md = render_markdown_report("2026-05-02", sections, suppressed_duplicate_count=5)
        self.assertIn("## Executive Summary", md)
        self.assertIn("### Top picks", md)
        self.assertIn("## New Papers", md)
        self.assertIn("## Updated Papers", md)
        self.assertIn("## Carry-over Papers", md)
        self.assertIn("## Suppressed Duplicates", md)
        self.assertIn("Why recommended:", md)
        self.assertIn("Action: Read now", md)
        self.assertIn("Count: **5**", md)


if __name__ == "__main__":
    unittest.main()
