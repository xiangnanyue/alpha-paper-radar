from alpha_paper_radar.cli import resolve_date, run


def test_resolve_date_format_passthrough():
    assert resolve_date("2026-05-02") == "2026-05-02"


def test_run_deduplicates_and_merges_topics(monkeypatch, capsys):
    monkeypatch.setattr(
        "alpha_paper_radar.cli.load_topics_config",
        lambda: {
            "topics": {
                "topic_a": {"categories": ["cs.LG"], "keywords": ["alpha"], "max_results": 10},
                "topic_b": {"categories": ["cs.AI"], "keywords": ["alpha"], "max_results": 10},
            }
        },
    )

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

    monkeypatch.setattr("alpha_paper_radar.cli.fetch_arxiv_papers", lambda categories, max_results: sample_papers)

    captured = {}

    def fake_save_jsonl(papers, output_path):
        captured["papers"] = papers
        captured["path"] = str(output_path)
        return output_path

    monkeypatch.setattr("alpha_paper_radar.cli.save_jsonl", fake_save_jsonl)
    monkeypatch.setattr("pathlib.Path.write_text", lambda self, content, encoding: len(content))

    run("2026-05-02")

    assert len(captured["papers"]) == 1
    assert captured["papers"][0]["topics"] == ["topic_a", "topic_b"]
    assert captured["path"].endswith("data/raw/2026-05-02.jsonl")

    out = capsys.readouterr().out
    assert "Saved 1 papers" in out


def test_run_dry_run_does_not_write(monkeypatch, capsys):
    monkeypatch.setattr(
        "alpha_paper_radar.cli.load_topics_config",
        lambda: {"topics": {"topic_a": {"categories": ["cs.LG"], "keywords": [], "max_results": 10}}},
    )
    monkeypatch.setattr("alpha_paper_radar.cli.fetch_arxiv_papers", lambda categories, max_results: [])

    called = {"save": False}

    def fake_save(*args, **kwargs):
        called["save"] = True

    monkeypatch.setattr("alpha_paper_radar.cli.save_jsonl", fake_save)
    run("2026-05-02", dry_run=True)

    assert called["save"] is False
    assert "[DRY RUN]" in capsys.readouterr().out
