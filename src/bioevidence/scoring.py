"""Deterministic, inspectable relevance and evidence prioritization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from bioevidence.models import Publication
from bioevidence.validation import unique_terms


@dataclass(frozen=True, slots=True)
class Score:
    """A bounded score with factors suitable for review by a domain specialist."""

    value: int
    factors: tuple[str, ...]


def score_publication(
    publication: Publication, interests: tuple[str, ...] | list[str] | None
) -> Score:
    """Score a publication from explicit matching, source, and recency factors."""
    normalized_interests = unique_terms(interests)
    searchable = f"{publication.title} {publication.abstract}".lower()
    matches = tuple(term for term in normalized_interests if term in searchable)
    points = min(60, len(matches) * 20)
    factors: list[str] = [f"Topic matches: {len(matches)}."]
    if publication.source == "PubMed":
        points += 20
        factors.append("Indexed PubMed record.")
    if _is_recent(publication.published_date):
        points += 20
        factors.append("Published within five years.")
    return Score(min(points, 100), tuple(factors))


def _is_recent(published_date: str) -> bool:
    """Safely identify a four-digit year no older than five calendar years."""
    try:
        return datetime.now(UTC).year - int(published_date[:4]) <= 5
    except (TypeError, ValueError):
        return False
