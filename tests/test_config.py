from alpha_paper_radar.config import load_topics_config


def test_load_topics_config_has_required_topics():
    data = load_topics_config("config/topics.yaml")
    topics = data["topics"]

    assert "quant_finance" in topics
    assert "deep_learning_sota" in topics
    assert "cross_section_time_series" in topics
    assert "llm_progress" in topics
