import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from remote_job_intelligence.main import run_actor


class ActorDefaultsTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_input_uses_the_documented_software_digest(self):
        actor = SimpleNamespace(
            get_input=AsyncMock(return_value={}),
            push_data=AsyncMock(return_value=SimpleNamespace(charged_count=0)),
            set_status_message=AsyncMock(),
            log=SimpleNamespace(warning=MagicMock(), info=MagicMock()),
        )
        report = {"warnings": [], "status": "ok", "sources": {}}

        with patch(
            "remote_job_intelligence.main.collect_jobs_with_status",
            return_value=([], report),
        ) as collect:
            await run_actor(actor)

        collect.assert_called_once_with(
            sources=None,
            keywords=["software"],
            locations=None,
            max_age_days=7,
            limit=20,
            include_description=False,
            keyword_match_mode="all",
        )

    def test_input_schema_exposes_the_same_defaults(self):
        schema_path = Path(__file__).parents[1] / ".actor" / "input_schema.json"
        properties = json.loads(schema_path.read_text())["properties"]

        self.assertEqual(properties["keywords"]["default"], ["software"])
        self.assertEqual(properties["maxAgeDays"]["default"], 7)
        self.assertEqual(properties["limit"]["default"], 20)


if __name__ == "__main__":
    unittest.main()
