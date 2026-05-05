from alpha_paper_radar.config import load_topics_config


def test_topics_have_rich_keyword_sets():
    cfg = load_topics_config("config/topics.yaml")
    topics = cfg["topics"]

    for name, topic_cfg in topics.items():
        keywords = topic_cfg["keywords"]
        assert len(keywords) >= 10, f"{name} should have at least 10 keywords"
        assert len(set(k.lower() for k in keywords)) == len(keywords), f"{name} keywords should be case-insensitively unique"


def test_topics_include_core_research_terms():
    cfg = load_topics_config("config/topics.yaml")
    topics = cfg["topics"]

    assert "portfolio optimization" in topics["quant_finance"]["keywords"]
    assert "scaling law" in topics["deep_learning_sota"]["keywords"]
    assert "fama-macbeth" in topics["cross_section_time_series"]["keywords"]
    assert "retrieval-augmented generation" in topics["llm_progress"]["keywords"]
