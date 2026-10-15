"""Run bounded Foundry drafts independently from the outbox and code judge."""

import argparse
import logging
import time

from socrat.config import DatabaseSettings
from socrat.database import make_engine
from socrat.foundry.config import FoundrySettings
from socrat.foundry.jobs import FoundryStopped, JobRequest, enqueue, run_once


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--stub-skill", help="Enqueue a synthetic skill; no crawling/model calls")
    parser.add_argument(
        "--live", action="store_true", help="Explicitly opt into permitted acquisition"
    )
    parser.add_argument("--skill", help="Canonical skill slug for an acquisition smoke job")
    parser.add_argument("--acquire-url", action="append", default=[])
    args = parser.parse_args()
    settings = FoundrySettings()
    if not settings.enabled:
        parser.error("Set SOCRAT_FOUNDRY_ENABLED=true to run offline stubs")
    if args.acquire_url and (not args.live or not settings.live_enabled or not args.skill):
        parser.error("Acquisition requires --live, --skill and SOCRAT_FOUNDRY_LIVE_ENABLED=true")
    if args.live and not args.acquire_url:
        parser.error("A live smoke run requires explicit --acquire-url inputs")
    engine = make_engine(DatabaseSettings().database_url_value)
    if engine.dialect.name == "sqlite" and not args.once:
        engine.dispose()
        parser.error(
            "SQLite supports --once single-worker development only; use PostgreSQL otherwise"
        )
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        handlers = None
        if args.acquire_url:
            from socrat.foundry.acquisition.stages import acquisition_handlers

            enqueue(
                engine,
                settings,
                JobRequest(
                    slug=args.skill,
                    title=args.skill.replace("-", " "),
                    payload={"urls": args.acquire_url},
                ),
            )
            handlers = acquisition_handlers(engine)
        if args.stub_skill:
            enqueue(
                engine,
                settings,
                JobRequest(slug=args.stub_skill, title=args.stub_skill.replace("-", " ")),
            )
        while True:
            try:
                run_once(engine, settings, handlers)
            except Exception:
                logging.error('{"event":"foundry_worker_failed"}')
                if args.once:
                    raise FoundryStopped("worker_failed") from None
            if args.once:
                break
            time.sleep(settings.poll_seconds)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
