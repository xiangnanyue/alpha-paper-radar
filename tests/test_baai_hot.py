import unittest
from pathlib import Path
from unittest.mock import patch

from alpha_paper_radar.baai_hot import (
    DAILY_SPEC,
    WEEKLY_SPEC,
    build_baai_hot_url,
    dedupe_baai_papers,
    extract_pdf_url,
    fetch_baai_hot_papers,
    match_topics,
    parse_baai_papers_html,
)
from alpha_paper_radar.baai_hot_registry import merge_baai_hot_papers
from alpha_paper_radar.baai_hot_report import render_baai_hot_report, select_fast_rising, select_latest, select_topic_matches


# Use the field boundaries that BAAI actually serves; plain anchor text cannot
# reliably distinguish the final title word from the first author's name.
LIST_HTML = """
<html><body>
<div class="papers-home-item">
<a href="/paper/abc-123">
<h6 class="papers-home-header__title">Scaling Behaviors of LLM Reinforcement Learning Post-Training</h6>
<span class="paper-author-name">Zelin Tan</span>, <span class="paper-author-name">Hejia Geng</span>
<span class="paper-author-name">...</span>
<span class="papers-home-item-time">2026年06月01日</span>
<div class="expandable-text__plain">这篇论文研究 large language model reasoning 和 reinforcement learning scaling。</div>
<b class="papers-home-hotness__num">1061</b> 热度
</a></div>
<div class="papers-home-item">
<a href="/paper/def-456"><h6 class="papers-home-header__title">Low Hotness Paper</h6>
<span class="paper-author-name">Jane Doe</span></a>
<span class="papers-home-item-time">2026年05月01日</span>
<div class="expandable-text__plain">摘要。</div>
<b class="papers-home-hotness__num">49</b> 热度
</div></body></html>
"""
REAL_HTML = (Path(__file__).parent / "fixtures" / "baai_hot_2026-11-07.html").read_text(encoding="utf-8")
HARNESS_ID = "4bc7d23c-3a98-481b-9790-8eaadbd4b50f"
HARNESS_TITLE = "How Do Coding-Agent Harnesses Self-Evolve? An Empirical Study of Retrospective Adaptation"


class TestBaaiHot(unittest.TestCase):
    def test_build_urls_keep_daily_and_weekly_separate(self):
        self.assertEqual(build_baai_hot_url(DAILY_SPEC.time), "https://hub.baai.ac.cn/papers")
        self.assertEqual(build_baai_hot_url(WEEKLY_SPEC.time), "https://hub.baai.ac.cn/papers?model=hotness&time=week")

    def test_parse_baai_papers_html_extracts_core_fields(self):
        papers = parse_baai_papers_html(LIST_HTML, source="daily", fetched_at="2026-06-05T00:00:00+00:00")
        self.assertEqual(len(papers), 2)
        self.assertEqual(papers[0]["id"], "abc-123")
        self.assertEqual(papers[0]["title"], "Scaling Behaviors of LLM Reinforcement Learning Post-Training")
        self.assertEqual(papers[0]["authors"], ["Zelin Tan", "Hejia Geng"])
        self.assertEqual(papers[1]["title"], "Low Hotness Paper")
        self.assertEqual(papers[1]["authors"], ["Jane Doe"])
        self.assertEqual(papers[0]["published"], "2026-06-01")
        self.assertEqual(papers[0]["hotness"], 1061)
        self.assertIn("large language model", papers[0]["summary"])
        self.assertEqual(papers[0]["priority"], "unscored")

    def test_real_cards_extract_exact_metadata(self):
        papers = parse_baai_papers_html(REAL_HTML, "weekly", "2026-11-07T00:00:00+00:00")
        expected = [
            (HARNESS_ID, HARNESS_TITLE, ["Christoph Treude", "Sebastian Baltes"], "2026-10-26", 4640),
            ("105e9eeb-bebc-4656-b62a-ae33446f0b1b",
             "The Little Book of Generative AI Foundations: An Intuitive Mathematical Primer",
             ["Tianhua Chen"], "2026-05-28", 986),
            ("40029513-50e6-4c6f-a658-207de33043b6", "LEANN: A Low-Storage Vector Index",
             ["Yichuan Wang", "Zhifei Li", "Shu Liu", "Yongji Wu", "Ziming Mao", "Yilong Zhao",
              "Xiao Yan", "Zhiying Xu", "Yang Zhou", "Ion Stoica"], "2025-06-09", 15057),
            ("e9847a14-bb0f-4a32-9411-351d0b502838",
             "Back to Basics: Let Denoising Generative Models Denoise",
             ["Tianhong Li", "Kaiming He"], "2025-11-17", 2811),
        ]
        self.assertEqual(len(papers), len(expected))
        for paper, (pid, title, authors, published, hotness) in zip(papers, expected):
            with self.subTest(id=pid):
                self.assertEqual(paper["id"], pid)
                self.assertEqual(paper["title"], title)
                self.assertEqual(paper["authors"], authors)
                self.assertEqual(paper["published"], published)
                self.assertEqual(paper["hotness"], hotness)
                self.assertEqual(paper["priority"], "unscored")
                self.assertEqual(paper["fetched_at"], "2026-11-07T00:00:00+00:00")
                self.assertTrue(paper["summary"])
                self.assertNotIn("热度", paper["summary"])
        self.assertTrue(papers[0]["summary"].startswith("编码智能体能够"))
        self.assertTrue(papers[0]["summary"].endswith("并据此对无效修改进行修订或移除。"))

    def test_inline_markup_entities_and_adjacent_equal_titles(self):
        html = LIST_HTML.replace("Low Hotness Paper", "Scaling Behaviors of LLM Reinforcement Learning Post-Training")
        html = html.replace("Zelin Tan", "Zelin <em>Tan</em>")
        html = html.replace("Jane Doe", "Jane &amp; Doe")
        papers = parse_baai_papers_html(html, "daily")
        self.assertEqual(len(papers), 2)
        self.assertEqual(papers[0]["title"], papers[1]["title"])
        self.assertEqual(papers[0]["authors"], ["Zelin Tan", "Hejia Geng"])
        self.assertEqual(papers[1]["authors"], ["Jane & Doe"])
        self.assertEqual([p["hotness"] for p in papers], [1061, 49])
        self.assertEqual([p["published"] for p in papers], ["2026-06-01", "2026-05-01"])

    def test_bad_required_fields_are_visible_failures(self):
        for html in [
            "<html>Unexpected page</html>",
            LIST_HTML.replace("1061", "1.06w"),
            LIST_HTML.replace("2026年06月01日", "2026年02月30日"),
            LIST_HTML.replace('class="papers-home-header__title"', 'class="changed-title"'),
        ]:
            with self.subTest(html=html[:80]), self.assertRaises(ValueError):
                parse_baai_papers_html(html, "daily")
        # The public fetch path already surfaces parse failures as fetch warnings.
        with patch("alpha_paper_radar.baai_hot.fetch_url", return_value="<html>Changed</html>"):
            with self.assertRaisesRegex(RuntimeError, "no recognized paper cards"):
                fetch_baai_hot_papers(DAILY_SPEC, enrich_pdf=False, max_retries=0)

    def test_payload_strings_cannot_impersonate_hotness_fields(self):
        fake = r'<script>{id:"abc-123",title:"fake hotness_value:\"9999\"",hotness_value:"1062"}</script>'
        papers = parse_baai_papers_html(LIST_HTML + fake, "daily")
        self.assertEqual(papers[0]["hotness"], 1062)

    def test_real_cards_preserve_dedupe_tracking_topics_and_clean_report(self):
        daily = parse_baai_papers_html(REAL_HTML, "daily")
        weekly = parse_baai_papers_html(REAL_HTML, "weekly")
        weekly[0]["hotness"] += 50
        papers = dedupe_baai_papers(daily + weekly)
        self.assertEqual(len(papers), 4)
        harness = next(p for p in papers if p["id"] == HARNESS_ID)
        self.assertEqual(harness["sources"], ["daily", "weekly"])
        self.assertEqual(harness["hotness"], 4690)
        cfg = {"topics": {"llm_progress": {"keywords": ["agent"]},
                          "tag_only": {"keywords": ["PVDAR", "AK's Picks"]}}}
        papers = match_topics(papers, cfg)
        harness = next(p for p in papers if p["id"] == HARNESS_ID)
        self.assertEqual(harness["topics"], ["llm_progress"])
        self.assertTrue(all("tag_only" not in p["topics"] for p in papers))
        registry, sections, _ = merge_baai_hot_papers({}, papers, "2026-11-07")
        report = render_baai_hot_report("2026-11-07", sections, 0)
        self.assertIn(HARNESS_TITLE + "\n", report)
        self.assertIn("- Authors: Christoph Treude, Sebastian Baltes\n", report)
        self.assertNotIn(HARNESS_TITLE + " " + HARNESS_TITLE, report)
        self.assertNotIn("根据论文相关帖子", report)
        registry, sections, suppressed = merge_baai_hot_papers(registry, papers, "2026-11-08")
        self.assertEqual(suppressed, 4)
        self.assertEqual(sections["new"], [])
        registry, _, _ = merge_baai_hot_papers(registry, [dict(harness, hotness=4740)], "2026-11-09")
        self.assertEqual(len(registry), 4)
        self.assertEqual(registry[HARNESS_ID]["hotness_delta"], 50)
        self.assertEqual(registry[HARNESS_ID]["peak_hotness"], 4740)
        self.assertEqual(len(registry[HARNESS_ID]["observations"]), 3)

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
