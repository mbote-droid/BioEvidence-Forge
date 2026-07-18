"""Review-ready Markdown reporting with retained source citations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

from bioevidence.models import Publication
from bioevidence.scoring import Score
from bioevidence.validation import safe_text


@dataclass(frozen=True, slots=True)
class ReportResult:
    """A report outcome with a path when writing completed successfully."""

    path: Path | None
    record_count: int
    message: str


class ReportWriter:
    """Write bounded, source-linked evidence briefs to a configured local directory."""

    def __init__(self, reports_path: Path) -> None:
        self._reports_path = reports_path

    def write(
        self, topic: object, scored_records: tuple[tuple[Publication, Score], ...]
    ) -> ReportResult:
        """Write a non-empty review brief or return a truthful failure result."""
        safe_topic = safe_text(topic, fallback="General biomedical research", limit=200)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = self._reports_path / f"evidence-brief-{timestamp}.md"
        try:
            self._reports_path.mkdir(parents=True, exist_ok=True)
            path.write_text(self._render(safe_topic, scored_records), encoding="utf-8")
            return ReportResult(
                path, len(scored_records), f"Report written with {len(scored_records)} record(s)."
            )
        except OSError as error:
            logger.error("Report write failed: {}", type(error).__name__)
            return ReportResult(None, len(scored_records), "Report write failed.")

    @staticmethod
    def _render(topic: str, scored_records: tuple[tuple[Publication, Score], ...]) -> str:
        heading = f"# Evidence brief: {topic}\n\n"
        notice = (
            "Human review is required before publication, clinical use, "
            "or external distribution.\n\n"
        )
        if not scored_records:
            return heading + notice + "No eligible records were collected for this run.\n"
        items = "\n".join(
            ReportWriter._item(index, publication, score)
            for index, (publication, score) in enumerate(scored_records, start=1)
        )
        return heading + notice + "## Prioritized records\n\n" + items

    @staticmethod
    def _item(index: int, publication: Publication, score: Score) -> str:
        factors = " ".join(score.factors)
        return (
            f"### {index}. {publication.title}\n\n"
            f"- Priority score: {score.value}/100\n"
            f"- Review factors: {factors}\n"
            f"- Citation: {publication.citation}\n"
            f"- Abstract: {ReportWriter._abstract_snippet(publication.abstract)}\n"
        )

    @staticmethod
    def _abstract_snippet(abstract: str, limit: int = 2_000) -> str:
        """Bound a pre-sanitized abstract without producing an empty report field."""
        bounded_limit = max(1, limit)
        return abstract[:bounded_limit] + ("..." if len(abstract) > bounded_limit else "")
