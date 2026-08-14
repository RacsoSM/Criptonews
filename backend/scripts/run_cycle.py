"""Standalone entrypoint for running one ingestion cycle outside the API process.

Invoked by the GitHub Actions hourly workflow (.github/workflows/hourly-cycle.yml),
which owns the schedule now that the backend no longer runs a resident process —
see app/main.py for why the in-process APScheduler was removed.
"""
from app.db import init_db
from app.scheduler import run_cycle


def main() -> None:
    init_db()
    run_cycle()


if __name__ == "__main__":
    main()
