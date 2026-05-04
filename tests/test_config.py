import unittest
from alpha_paper_radar.config import load_topics_config

class TestConfig(unittest.TestCase):
    def test_load_topics_config_has_required_topics(self):
        data = load_topics_config("config/topics.yaml")
        topics = data["topics"]
        self.assertIn("quant_finance", topics)
        self.assertIn("deep_learning_sota", topics)
        self.assertIn("cross_section_time_series", topics)
        self.assertIn("llm_progress", topics)

if __name__ == "__main__":
    unittest.main()
