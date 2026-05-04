import unittest
from alpha_paper_radar.filter_papers import filter_papers_by_keywords

class TestFilterPapers(unittest.TestCase):
    def test_filter_no_keywords_returns_all(self):
        papers = [{"title": "A", "summary": "B"}]
        self.assertEqual(filter_papers_by_keywords(papers, []), papers)

    def test_filter_case_insensitive_and_summary_match(self):
        papers = [{"title": "Attention Is All You Need", "summary": "Transformer"}, {"title": "Factor investing", "summary": "Cross-sectional alpha"}]
        filtered = filter_papers_by_keywords(papers, ["transformer", "ALPHA"])
        self.assertEqual(len(filtered), 2)

    def test_filter_non_match_returns_empty(self):
        papers = [{"title": "A", "summary": "B"}]
        self.assertEqual(filter_papers_by_keywords(papers, ["notfound"]), [])

if __name__ == "__main__":
    unittest.main()
