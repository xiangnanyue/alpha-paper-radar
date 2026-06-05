import unittest

from alpha_paper_radar.baai_hot import (
    DAILY_SPEC,
    WEEKLY_SPEC,
    build_baai_hot_url,
    dedupe_baai_papers,
    extract_pdf_url,
    match_topics,
    parse_baai_papers_html,
)
from alpha_paper_radar.baai_hot_registry import merge_baai_hot_papers
from alpha_paper_radar.baai_hot_report import render_baai_hot_report, select_fast_rising, select_latest, select_topic_matches


LIST_HTML = """
<html><body>
<a href="/paper/abc-123">Scaling Behaviors of LLM Reinforcement Learning Post-Training Zelin Tan , Hejia Geng , ...</a>
2026年06月01日 这篇论文研究 large language model reasoning 和 reinforcement learning scaling。 1061 热度
PDF
<a href="/paper/def-456">Low Hotness Paper Jane Doe</a>
2026年05月01日 摘要。 49 热度
</body></html>
"""


class TestBaaiHot(unittest.TestCase):
    def test_build_urls_keep_daily_and_weekly_separate(self):
        self.assertEqual(build_baai_hot_url(DAILY_SPEC.time), "https://hub.baai.ac.cn/papers")
        self.assertEqual(build_baai_hot_url(WEEKLY_SPEC.time), "https://hub.baai.ac.cn/papers?model=hotness&time=week")

    def test_parse_baai_papers_html_extracts_core_fields(self):
        papers = parse_baai_papers_html(LIST_HTML, source="daily", fetched_at="2026-06-05T00:00:00+00:00")
        self.assertEqual(len(papers), 2)
        self.assertEqual(papers[0]["id"], "abc-123")
        self.assertEqual(papers[0]["published"], "2026-06-01")
        self.assertEqual(papers[0]["hotness"], 1061)
        self.assertIn("large language model", papers[0]["summary"])
        self.assertEqual(papers[0]["priority"], "unscored")

    def test_extract_pdf_url_from_detail_page(self):
        html = '<a href="https://arxiv.org/pdf/2606.00001.pdf">PDF</a>'
        self.assertEqual(extract_pdf_url(html), "https://arxiv.org/pdf/2606.00001.pdf")

    def test_dedupe_prefers_max_hotness_and_merges_sources(self):
        papers = [
            {"id": "x", "title": "A", "hotness": 100, "source": "daily", "summary": "", "pdf_url": ""},
            {"id": "x", "title": "A", "hotness": 600, "source": "weekly", "summary": "s", "pdf_url": "p"},
        ]
        deduped = dedupe_baai_papers(papers)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0]["hotness"], 600)
        self.assertEqual(deduped[0]["sources"], ["daily", "weekly"])
        self.assertEqual(deduped[0]["summary"], "s")

    def test_match_topics_reuses_existing_topic_keywords(self):
        papers = [{"id": "x", "title": "LLM agent", "summary": "tool use and rag", "hotness": 100}]
        cfg = {"topics": {"llm_progress": {"keywords": ["agent", "rag"]}, "quant_finance": {"keywords": ["portfolio"]}}}
        matched = match_topics(papers, cfg)
        self.assertEqual(matched[0]["topics"], ["llm_progress"])
        self.assertEqual(matched[0]["matched_keywords"], {"llm_progress": ["agent", "rag"]})

    def test_merge_registry_updates_hotness_without_duplicating_paper_records(self):
        registry = {}
        paper = {"id": "x", "title": "A", "hotness": 100, "summary": "s", "topics": ["llm_progress"], "priority": "unscored"}
        registry, sections, suppressed = merge_baai_hot_papers(registry, [paper], "2026-06-04")
        self.assertEqual(len(sections["new"]), 1)
        self.assertEqual(suppressed, 0)
        registry, sections, suppressed = merge_baai_hot_papers(registry, [dict(paper, hotness=150)], "2026-06-05")
        self.assertEqual(len(registry), 1)
        self.assertEqual(len(sections["updated"]), 1)
        self.assertEqual(registry["x"]["latest_hotness"], 150)
        self.assertEqual(registry["x"]["hotness_delta"], 50)
        self.assertEqual(len(registry["x"]["observations"]), 2)

    def test_report_sections_cover_rising_latest_and_topics(self):
        papers = [
            {"id": "x", "title": "A", "latest_hotness": 150, "hotness_delta": 50, "published": "2026-06-04", "topics": ["llm_progress"]},
            {"id": "y", "title": "B", "latest_hotness": 90, "hotness_delta": 0, "published": "2026-05-01", "topics": []},
        ]
        self.assertEqual(select_fast_rising(papers)[0]["id"], "x")
        self.assertEqual(select_latest(papers, "2026-06-05")[0]["id"], "x")
        self.assertEqual(select_topic_matches(papers)[0]["id"], "x")
        report = render_baai_hot_report("2026-06-05", {"new": papers, "updated": [], "carryover": []}, 0)
        self.assertIn("## Fast Rising Papers", report)
        self.assertIn("## Latest Papers", report)
        self.assertIn("## Topic Matches", report)

    def test_report_includes_fetch_warnings(self):
        report = render_baai_hot_report(
            "2026-06-05",
            {"new": [], "updated": [], "carryover": []},
            0,
            fetch_warnings=["Failed to fetch BAAI daily list: network blocked"],
        )
        self.assertIn("## Fetch Warnings", report)
        self.assertIn("network blocked", report)


if __name__ == "__main__":
    unittest.main()
