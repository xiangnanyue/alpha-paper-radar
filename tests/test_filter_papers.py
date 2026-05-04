from alpha_paper_radar.filter_papers import filter_papers_by_keywords


def test_filter_no_keywords_returns_all():
    papers = [{"title": "A", "summary": "B"}]
    assert filter_papers_by_keywords(papers, []) == papers


def test_filter_case_insensitive_and_summary_match():
    papers = [
        {"title": "Attention Is All You Need", "summary": "Transformer"},
        {"title": "Factor investing", "summary": "Cross-sectional alpha"},
    ]

    filtered = filter_papers_by_keywords(papers, ["transformer", "ALPHA"])
    assert len(filtered) == 2


def test_filter_non_match_returns_empty():
    papers = [{"title": "A", "summary": "B"}]
    assert filter_papers_by_keywords(papers, ["notfound"]) == []
