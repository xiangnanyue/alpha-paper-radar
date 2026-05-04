import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from alpha_paper_radar.cli import resolve_date, run


class TestCli(unittest.TestCase):
    def test_resolve_date_format_passthrough(self):
        self.assertEqual(resolve_date("2026-05-02"), "2026-05-02")

    def test_run_deduplicates_and_merges_topics(self):
        sample_papers = [
            {
                "id": "http://arxiv.org/abs/1.0001",
                "title": "Alpha Model",
                "summary": "alpha signal",
                "authors": ["A"],
                "published": "2026-05-01T00:00:00Z",
                "priority": "unscored",
            }
        ]
        captured = {}

        def fake_save_jsonl(papers, output_path):
            captured["papers"] = papers
            captured["path"] = str(output_path)
            return output_path

        with patch("alpha_paper_radar.cli.load_topics_config", return_value={"topics": {
            "topic_a": {"categories": ["cs.LG"], "keywords": ["alpha"], "max_results": 10},
            "topic_b": {"categories": ["cs.AI"], "keywords": ["alpha"], "max_results": 10},
        }}), patch("alpha_paper_radar.cli.fetch_arxiv_papers", return_value=sample_papers), patch(
            "alpha_paper_radar.cli.save_jsonl", side_effect=fake_save_jsonl
        ), patch("alpha_paper_radar.cli.load_registry", return_value={}), patch(
            "alpha_paper_radar.cli.save_registry", return_value=None
        ), patch("pathlib.Path.write_text", return_value=0):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                run("2026-05-02")

        self.assertEqual(len(captured["papers"]), 1)
        self.assertEqual(captured["papers"][0]["topics"], ["topic_a", "topic_b"])
        self.assertTrue(captured["path"].endswith("data/raw/2026-05-02.jsonl"))
        self.assertIn("Saved 1 papers", stdout.getvalue())

    def test_run_dry_run_does_not_write(self):
        with patch("alpha_paper_radar.cli.load_topics_config", return_value={"topics": {"topic_a": {"categories": ["cs.LG"], "keywords": [], "max_results": 10}}}), patch(
            "alpha_paper_radar.cli.fetch_arxiv_papers", return_value=[]
        ), patch("alpha_paper_radar.cli.save_jsonl") as mock_save:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                run("2026-05-02", dry_run=True)

        mock_save.assert_not_called()
        self.assertIn("[DRY RUN]", stdout.getvalue())

    def test_run_skips_report_when_no_new_or_updated(self):
        with patch("alpha_paper_radar.cli.load_topics_config", return_value={"topics": {"topic_a": {"categories": ["cs.LG"], "keywords": [], "max_results": 10}}}), patch(
            "alpha_paper_radar.cli.fetch_arxiv_papers", return_value=[]
        ), patch("alpha_paper_radar.cli.save_jsonl", return_value=None), patch(
            "alpha_paper_radar.cli.load_registry", return_value={}
        ), patch("alpha_paper_radar.cli.save_registry", return_value=None), patch(
            "pathlib.Path.write_text", return_value=0
        ) as mock_write, patch("pathlib.Path.unlink", return_value=None) as mock_unlink:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                run("2026-05-02")

        mock_write.assert_not_called()
        mock_unlink.assert_called_once()
        self.assertIn("Skipped report generation", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
