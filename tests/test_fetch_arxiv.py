import unittest
from alpha_paper_radar.fetch_arxiv import parse_arxiv_feed

SAMPLE_XML = """<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom'>
  <entry>
    <id>http://arxiv.org/abs/1234.5678</id>
    <updated>2026-05-01T00:00:00Z</updated>
    <published>2026-05-01T00:00:00Z</published>
    <title>  Sample Paper  </title>
    <summary>  Sample Summary  </summary>
    <author><name>Alice</name></author>
    <author><name>Bob</name></author>
    <category term='cs.LG'/>
  </entry>
</feed>
"""

class TestFetchArxiv(unittest.TestCase):
    def test_parse_arxiv_feed_extracts_fields_and_priority(self):
        papers = parse_arxiv_feed(SAMPLE_XML)
        self.assertEqual(len(papers), 1)
        paper = papers[0]
        self.assertEqual(paper["id"], "http://arxiv.org/abs/1234.5678")
        self.assertEqual(paper["title"], "Sample Paper")
        self.assertEqual(paper["summary"], "Sample Summary")
        self.assertEqual(paper["authors"], ["Alice", "Bob"])
        self.assertEqual(paper["categories"], ["cs.LG"])
        self.assertEqual(paper["priority"], "unscored")
        self.assertIn("fetched_at", paper)

if __name__ == "__main__":
    unittest.main()
