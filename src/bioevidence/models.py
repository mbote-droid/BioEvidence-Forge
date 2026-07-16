"""Validated, immutable data contracts used by the research workflow."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from bioevidence.validation import safe_identifier, safe_text, unique_terms


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Publication:
    """A source-traceable publication record safe for local persistence."""

    identifier: str
    title: str
    abstract: str
    source: str
    source_url: str
    authors: tuple[str, ...] = field(default_factory=tuple)
    published_date: str = "Unavailable"
    retrieved_at: datetime = field(default_factory=utc_now)
    topics: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object] | None) -> Publication:
        """Create a safe record from an untrusted mapping."""
        value = payload or {}
        authors = value.get("authors", ())
        author_values = authors if isinstance(authors, (list, tuple)) else ()
        return cls(
            identifier=safe_identifier(value.get("identifier")),
            title=safe_text(value.get("title")),
            abstract=safe_text(value.get("abstract")),
            source=safe_text(value.get("source"), fallback="Unknown source", limit=160),
            source_url=safe_text(value.get("source_url"), fallback="Unavailable", limit=2_000),
            authors=tuple(
                safe_text(author, fallback="", limit=160) for author in author_values if author
            )[:50],
            published_date=safe_text(value.get("published_date"), limit=64),
            topics=unique_terms(
                value.get("topics") if isinstance(value.get("topics"), (list, tuple)) else ()
            ),
        )

    @property
    def citation(self) -> str:
        """Return a non-empty human-readable citation string."""
        author_text = ", ".join(self.authors) if self.authors else "Authors unavailable"
        return (
            f"{author_text}. {self.title}. {self.source} ({self.published_date}). {self.source_url}"
        )
