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


def test_parse_arxiv_feed_extracts_fields_and_priority():
    papers = parse_arxiv_feed(SAMPLE_XML)
    assert len(papers) == 1
    paper = papers[0]
    assert paper["id"] == "http://arxiv.org/abs/1234.5678"
    assert paper["title"] == "Sample Paper"
    assert paper["summary"] == "Sample Summary"
    assert paper["authors"] == ["Alice", "Bob"]
    assert paper["categories"] == ["cs.LG"]
    assert paper["priority"] == "unscored"
    assert "fetched_at" in paper
