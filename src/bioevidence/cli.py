"""Command-line entrypoints for local collection and continuous operation."""

from __future__ import annotations

import argparse
from threading import Event

from loguru import logger

from bioevidence.config import Settings
from bioevidence.pipeline import ResearchPipeline
from bioevidence.reporting import ReportWriter
from bioevidence.scheduler import PeriodicRunner
from bioevidence.sources.pubmed import PubMedClient
from bioevidence.storage import PublicationStore


def build_pipeline(settings: Settings) -> ResearchPipeline:
    """Construct the local workflow using the supplied validated settings."""
    return ResearchPipeline(
        PubMedClient(
            contact_email=settings.contact_email,
            api_key=settings.ncbi_api_key,
            timeout_seconds=settings.request_timeout_seconds,
            max_results=settings.max_results,
        ),
        PublicationStore(settings.database_path),
        ReportWriter(settings.reports_path),
    )


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    """Parse a compact, validation-friendly local command interface."""
    parser = argparse.ArgumentParser(prog="bioevidence")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("collect", "schedule"):
        child = subparsers.add_parser(command)
        child.add_argument("topic", nargs="?", default="general biomedical research")
    subparsers.add_parser("health")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    """Execute a local command and return a conventional process status code."""
    args = parse_args(arguments)
    settings = Settings.from_mapping()
    store = PublicationStore(settings.database_path)
    if args.command == "health":
        result = store.count()
        logger.info(result.message)
        return 0
    pipeline = build_pipeline(settings)
    if args.command == "collect":
        try:
            logger.info(pipeline.run(args.topic).message)
        finally:
            _close_pipeline(pipeline)
        return 0
    runner = PeriodicRunner(pipeline, args.topic, settings.poll_interval_minutes)
    try:
        runner.run_forever(Event(), lambda result: logger.info(result.message))
    except KeyboardInterrupt:
        logger.info("Scheduler stopped.")
    finally:
        _close_pipeline(pipeline)
    return 0


def _close_pipeline(pipeline: ResearchPipeline) -> bool:
    """Close a workflow source if the supplied workflow supports cleanup."""
    closer = getattr(pipeline, "close", None)
    return bool(closer()) if callable(closer) else False


if __name__ == "__main__":
    raise SystemExit(main())
