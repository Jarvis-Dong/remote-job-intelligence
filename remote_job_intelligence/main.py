"""Apify runtime entry point."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .core import collect_jobs


async def run_actor(actor: object) -> None:
    actor_input = await actor.get_input() or {}
    if not isinstance(actor_input, dict):
        raise ValueError("Actor input must be an object")
    jobs = collect_jobs(
        sources=actor_input.get("sources"),
        keywords=actor_input.get("keywords"),
        locations=actor_input.get("locations"),
        max_age_days=actor_input.get("maxAgeDays", 14),
        limit=actor_input.get("limit", 50),
        include_description=actor_input.get("includeDescription", False),
    )
    charge = await actor.push_data(jobs)
    if charge.charged_count < len(jobs):
        actor.log.info("Charge limit reached; returned only charged records")
    await actor.set_status_message(f"Returned {charge.charged_count} normalized remote jobs")


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
