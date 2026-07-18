"""Application configuration loaded from a validated environment mapping."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


def _positive_int(value: str | None, default: int, minimum: int = 1) -> int:
    """Return a bounded integer, falling back when the supplied value is unsuitable."""
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= minimum else default


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings with local paths and conservative resource limits."""

    database_path: Path
    reports_path: Path
    contact_email: str
    ncbi_api_key: str
    request_timeout_seconds: int
    max_results: int
    poll_interval_minutes: int

    @classmethod
    def from_mapping(cls, values: Mapping[str, str] | None = None) -> Settings:
        """Build settings from an environment-like mapping without raising on malformed values."""
        source = values if values is not None else os.environ
        return cls(
            database_path=Path(source.get("BIOEVIDENCE_DATABASE_PATH", "data/bioevidence.sqlite3")),
            reports_path=Path(source.get("BIOEVIDENCE_REPORTS_PATH", "reports")),
            contact_email=source.get("BIOEVIDENCE_CONTACT_EMAIL", "").strip(),
            ncbi_api_key=source.get("BIOEVIDENCE_NCBI_API_KEY", "").strip(),
            request_timeout_seconds=_positive_int(
                source.get("BIOEVIDENCE_REQUEST_TIMEOUT_SECONDS"), 20
            ),
            max_results=_positive_int(source.get("BIOEVIDENCE_MAX_RESULTS"), 20),
            poll_interval_minutes=_positive_int(
                source.get("BIOEVIDENCE_POLL_INTERVAL_MINUTES"),
                360,
            ),
        )
