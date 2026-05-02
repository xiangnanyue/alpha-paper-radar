from alpha_paper_radar.render_report import render_markdown_report


def test_render_markdown_report_contains_sections():
    topic_to_papers = {
        "quant_finance": [
            {
                "id": "http://arxiv.org/abs/1234.5678",
                "title": "A Great Paper",
                "authors": ["Alice", "Bob"],
                "published": "2026-01-01T00:00:00Z",
                "priority": "unscored",
            }
        ],
        "llm_progress": [],
    }

    md = render_markdown_report("2026-05-02", topic_to_papers)

    assert "# Alpha Paper Radar - 2026-05-02" in md
    assert "## quant_finance" in md
    assert "A Great Paper" in md
    assert "Priority: unscored" in md
    assert "## llm_progress" in md
    assert "No matched papers" in md
