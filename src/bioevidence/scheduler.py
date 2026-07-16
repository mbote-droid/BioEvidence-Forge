"""Interruptible periodic execution for a continuously running research service."""

from __future__ import annotations

from collections.abc import Callable
from threading import Event

from loguru import logger

from bioevidence.pipeline import ResearchPipeline, RunResult
from bioevidence.validation import safe_text


class PeriodicRunner:
    """Run one configured research topic repeatedly without busy waiting."""

    def __init__(self, pipeline: ResearchPipeline, topic: object, interval_minutes: int) -> None:
        self._pipeline = pipeline
        self._topic = safe_text(topic, fallback="general biomedical research", limit=500)
        self._interval_seconds = max(60, interval_minutes * 60)

    def run_once(self) -> RunResult:
        """Run the workflow once and delegate its safe failure behavior."""
        return self._pipeline.run(self._topic)

    def run_forever(
        self, stop_event: Event, on_complete: Callable[[RunResult], None] | None = None
    ) -> None:
        """Repeat runs until requested to stop, keeping callback errors contained."""
        while not stop_event.is_set():
            result = self.run_once()
            if on_complete:
                try:
                    on_complete(result)
                except Exception as error:
                    logger.warning("Completion callback failed: {}", type(error).__name__)
            stop_event.wait(self._interval_seconds)
