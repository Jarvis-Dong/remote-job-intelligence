import unittest
from pathlib import Path


class ReadmeTests(unittest.TestCase):
    def test_links_both_public_examples(self):
        readme = (Path(__file__).parents[1] / "README.md").read_text()
        self.assertIn("/examples/daily-remote-software-jobs", readme)
        self.assertIn("/examples/daily-remote-ai-and-machine-learning-jobs", readme)


if __name__ == "__main__":
    unittest.main()
