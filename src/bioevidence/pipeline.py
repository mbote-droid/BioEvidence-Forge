"""Composable collection-to-report workflow with explicit outcomes."""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from bioevidence.reporting import ReportResult, ReportWriter
from bioevidence.scoring import Score, score_publication
from bioevidence.sources.pubmed import PubMedClient
from bioevidence.storage import PublicationStore, StorageResult
from bioevidence.validation import safe_text, unique_terms


@dataclass(frozen=True, slots=True)
class RunResult:
    """The complete result of one bounded research-monitoring run."""

    topic: str
    collected: int
    stored: StorageResult
    report: ReportResult
    message: str


class ResearchPipeline:
    """Collect, store, score, and report evidence for one research topic."""

    def __init__(self, source: PubMedClient, store: PublicationStore, writer: ReportWriter) -> None:
        self._source = source
        self._store = store
        self._writer = writer

    def run(self, topic: object) -> RunResult:
        """Execute one safe workflow run; failures become an honest report outcome."""
        normalized_topic = safe_text(topic, fallback="general biomedical research", limit=500)
        try:
            collected = self._source.search(normalized_topic)
            stored = self._store.upsert(collected.records)
            scored = self._score(collected.records, unique_terms(normalized_topic.split()))
            report = self._writer.write(normalized_topic, scored)
            return RunResult(
                normalized_topic,
                len(collected.records),
                stored,
                report,
                f"{collected.message} {stored.message} {report.message}",
            )
        except Exception as error:
            logger.exception("Pipeline run failed: {}", type(error).__name__)
            empty_report = self._writer.write(normalized_topic, ())
            return RunResult(
                normalized_topic,
                0,
                StorageResult(0, "Storage was not attempted."),
                empty_report,
                "Pipeline failed safely; inspect service logs before retrying.",
            )

    def close(self) -> bool:
        """Release a source resource when that connector owns one."""
        closer = getattr(self._source, "close", None)
        return bool(closer()) if callable(closer) else False

    @staticmethod
    def _score(records, interests: tuple[str, ...]) -> tuple[tuple[object, Score], ...]:
        scored = tuple((record, score_publication(record, interests)) for record in records)
        return tuple(sorted(scored, key=lambda item: item[1].value, reverse=True))
