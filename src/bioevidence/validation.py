"""Small, dependency-free guardrails for external text and identifiers."""

from __future__ import annotations

import html
import re
from collections.abc import Iterable

_WHITESPACE = re.compile(r"\s+")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:/-]{1,160}$")


def safe_text(value: object, fallback: str = "Unavailable", limit: int = 10_000) -> str:
    """Return escaped, space-normalized text with a non-empty bounded fallback."""
    normalized = _WHITESPACE.sub(" ", str(value or "")).strip()
    if not normalized:
        return fallback
    return html.escape(normalized[: max(1, limit)], quote=True)


def safe_identifier(value: object, fallback: str = "unknown") -> str:
    """Return a constrained external identifier or a known safe fallback."""
    candidate = str(value or "").strip()
    return candidate if _IDENTIFIER.fullmatch(candidate) else fallback


def unique_terms(values: Iterable[object] | None, limit: int = 20) -> tuple[str, ...]:
    """Normalize a term sequence, preserving order and returning a non-empty tuple."""
    seen: set[str] = set()
    output: list[str] = []
    for value in values or ():
        term = safe_text(value, fallback="", limit=160).lower()
        if term and term not in seen:
            seen.add(term)
            output.append(term)
        if len(output) >= max(1, limit):
            break
    return tuple(output) or ("general biomedical research",)
