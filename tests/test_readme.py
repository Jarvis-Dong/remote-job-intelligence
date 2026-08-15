import unittest
from pathlib import Path


class ReadmeTests(unittest.TestCase):
    def test_links_both_public_examples(self):
        readme = (Path(__file__).parents[1] / "README.md").read_text()
        self.assertIn("/examples/daily-remote-software-jobs", readme)
        self.assertIn("/examples/daily-remote-ai-and-machine-learning-jobs", readme)

    def test_readme_exposes_a_complete_api_input(self):
        readme = (Path(__file__).parents[1] / "README.md").read_text()

        self.assertIn(
            "ai-coding-radar~remote-job-intelligence/run-sync-get-dataset-items",
            readme,
        )
        self.assertIn('"keywords":["software"]', readme)
        self.assertIn('"maxAgeDays":7', readme)
        self.assertIn('"limit":20', readme)
        self.assertIn('"includeDescription":false', readme)

    def test_readme_shows_the_fixture_backed_output_shape(self):
        readme = (Path(__file__).parents[1] / "README.md").read_text()

        self.assertIn("Fixture-backed sample output", readme)
        self.assertIn('"id": "arbeitnow:sample-python"', readme)
        self.assertIn('"jobTitle": "Python Engineer"', readme)
        self.assertIn('"applyUrl": "https://example.com/jobs/python-engineer"', readme)


if __name__ == "__main__":
    unittest.main()
