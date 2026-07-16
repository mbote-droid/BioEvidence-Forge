"""Local SQLite persistence with parameterized statements and immutable source records."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from bioevidence.models import Publication


@dataclass(frozen=True, slots=True)
class StorageResult:
    """Safe storage outcome carrying a count and explanatory message."""

    count: int
    message: str


class PublicationStore:
    """A lightweight local archive suitable for constrained machines."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def initialize(self) -> StorageResult:
        """Create the archive schema idempotently."""
        try:
            self._database_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS publications (
                        identifier TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        abstract TEXT NOT NULL,
                        source TEXT NOT NULL,
                        source_url TEXT NOT NULL,
                        authors_json TEXT NOT NULL,
                        published_date TEXT NOT NULL,
                        retrieved_at TEXT NOT NULL,
                        topics_json TEXT NOT NULL
                    )
                    """
                )
            return StorageResult(0, "Archive is ready.")
        except sqlite3.Error as error:
            logger.error("Archive initialization failed: {}", type(error).__name__)
            return StorageResult(0, "Archive initialization failed.")

    def upsert(self, records: tuple[Publication, ...]) -> StorageResult:
        """Store records by stable identifier without duplicating a source record."""
        if not records:
            return StorageResult(0, "No records were provided for storage.")
        if self.initialize().message != "Archive is ready.":
            return StorageResult(0, "Archive is unavailable.")
        try:
            with self._connect() as connection:
                connection.executemany(
                    """
                    INSERT INTO publications (
                        identifier, title, abstract, source, source_url, authors_json,
                        published_date, retrieved_at, topics_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(identifier) DO UPDATE SET
                        title=excluded.title, abstract=excluded.abstract, source=excluded.source,
                        source_url=excluded.source_url, authors_json=excluded.authors_json,
                        published_date=excluded.published_date, retrieved_at=excluded.retrieved_at,
                        topics_json=excluded.topics_json
                    """,
                    tuple(self._row(record) for record in records),
                )
            return StorageResult(len(records), f"Stored {len(records)} record(s).")
        except sqlite3.Error as error:
            logger.error("Archive write failed: {}", type(error).__name__)
            return StorageResult(0, "Archive write failed.")

    def recent(self, limit: int = 20) -> tuple[Publication, ...]:
        """Return most recently collected records, safely bounded by a caller limit."""
        bounded_limit = max(1, min(limit, 100))
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT identifier, title, abstract, source, source_url, authors_json,
                           published_date, retrieved_at, topics_json
                    FROM publications ORDER BY retrieved_at DESC LIMIT ?
                    """,
                    (bounded_limit,),
                ).fetchall()
            return tuple(self._publication(row) for row in rows)
        except sqlite3.Error as error:
            logger.warning("Archive read failed: {}", type(error).__name__)
            return ()

    def count(self) -> StorageResult:
        """Return a count-bearing result even if the archive is unavailable."""
        try:
            with self._connect() as connection:
                count = connection.execute("SELECT COUNT(*) FROM publications").fetchone()[0]
            return StorageResult(int(count), f"Archive contains {count} record(s).")
        except sqlite3.Error as error:
            logger.warning("Archive count failed: {}", type(error).__name__)
            return StorageResult(0, "Archive is unavailable.")

    @contextmanager
    def _connect(self):
        """Yield a local connection and close it even when a query fails."""
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        except BaseException:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _row(record: Publication) -> tuple[str, str, str, str, str, str, str, str, str]:
        return (
            record.identifier,
            record.title,
            record.abstract,
            record.source,
            record.source_url,
            json.dumps(record.authors),
            record.published_date,
            record.retrieved_at.isoformat(),
            json.dumps(record.topics),
        )

    @staticmethod
    def _publication(row: sqlite3.Row) -> Publication:
        return Publication.from_mapping(
            {
                "identifier": row["identifier"],
                "title": row["title"],
                "abstract": row["abstract"],
                "source": row["source"],
                "source_url": row["source_url"],
                "authors": json.loads(row["authors_json"]),
                "published_date": row["published_date"],
                "topics": json.loads(row["topics_json"]),
            }
        )
