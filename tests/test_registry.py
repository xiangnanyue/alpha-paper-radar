import unittest
from alpha_paper_radar.registry import merge_into_registry, parse_arxiv_id

class TestRegistry(unittest.TestCase):
    def test_parse_arxiv_id_canonical_and_version(self):
        canonical, version = parse_arxiv_id("http://arxiv.org/abs/2605.01234v2")
        self.assertEqual(canonical, "2605.01234")
        self.assertEqual(version, 2)

    def test_merge_registry_new_and_updated_and_suppressed(self):
        registry = {}
        papers = [{"id": "http://arxiv.org/abs/2605.01234v1", "title": "T", "summary": "S", "authors": ["A"], "categories": ["cs.LG"], "primary_category": "cs.LG", "published": "2026-05-01T00:00:00Z", "updated": "2026-05-01T00:00:00Z", "topics": ["x"]}]
        registry, sections, suppressed = merge_into_registry(registry, papers, "2026-05-02")
        self.assertEqual(len(sections["new"]), 1)
        self.assertEqual(suppressed, 0)
        papers_v2 = [dict(papers[0], id="http://arxiv.org/abs/2605.01234v2", updated="2026-05-03T00:00:00Z")]
        registry, sections, suppressed = merge_into_registry(registry, papers_v2, "2026-05-03")
        self.assertEqual(len(sections["updated"]), 1)
        self.assertEqual(registry["2605.01234"]["latest_version"], 2)
        self.assertEqual(suppressed, 0)
        registry, sections, suppressed = merge_into_registry(registry, papers_v2, "2026-05-04")
        self.assertEqual(len(sections["updated"]), 0)
        self.assertEqual(suppressed, 1)

if __name__ == "__main__":
    unittest.main()
