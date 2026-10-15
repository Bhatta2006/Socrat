"""Run the M1 offline stub pipeline, independently from the outbox and code judge."""

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
    args = parser.parse_args()
    settings = FoundrySettings()
    if not settings.enabled:
        parser.error("Set SOCRAT_FOUNDRY_ENABLED=true to run offline stubs")
    engine = make_engine(DatabaseSettings().database_url_value)
    if engine.dialect.name == "sqlite" and not args.once:
        engine.dispose()
        parser.error(
            "SQLite supports --once single-worker development only; use PostgreSQL otherwise"
        )
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        if args.stub_skill:
            enqueue(
                engine,
                settings,
                JobRequest(slug=args.stub_skill, title=args.stub_skill.replace("-", " ")),
            )
        while True:
            try:
                run_once(engine, settings)
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
