"""Apify runtime entry point."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .core import collect_jobs, collect_jobs_with_status


async def run_actor(actor: object) -> None:
    actor_input = await actor.get_input() or {}
    if not isinstance(actor_input, dict):
        raise ValueError("Actor input must be an object")
    jobs, report = collect_jobs_with_status(
        sources=actor_input.get("sources"),
        keywords=actor_input.get("keywords", ["software"]),
        locations=actor_input.get("locations"),
        max_age_days=actor_input.get("maxAgeDays", 7),
        limit=actor_input.get("limit", 20),
        include_description=actor_input.get("includeDescription", False),
        keyword_match_mode=actor_input.get("keywordMatchMode", "all"),
    )
    for warning in report["warnings"]:
        actor.log.warning(warning)
    charge = await actor.push_data(jobs)
    if charge.charged_count < len(jobs):
        actor.log.info("Charge limit reached; returned only charged records")
    source_summary = ", ".join(
        f"{source}:{status['status']}"
        for source, status in report["sources"].items()
    )
    await actor.set_status_message(
        f"Returned {charge.charged_count} normalized remote jobs ({report['status']}; {source_summary})"
    )


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, help="run offline with a JSON payload map")
    args = parser.parse_args()
    if args.fixture:
        payloads = json.loads(args.fixture.read_text())
        jobs = collect_jobs(
            sources=list(payloads),
            payloads=payloads,
            now=datetime(2026, 8, 14, tzinfo=timezone.utc),
        )
        print(json.dumps(jobs, ensure_ascii=False, indent=2))
        return

    from apify import Actor

    async with Actor:
        await run_actor(Actor)
