"""Local SQLite persistence with parameterized statements and immutable source records."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from bioevidence.models import Publication

_SCHEMA_VERSION = "2"


@dataclass(frozen=True, slots=True)
class StorageResult:
    """Safe storage outcome carrying a count and explanatory message."""

    count: int
    message: str
    ok: bool = True


class PublicationStore:
    """A lightweight local archive suitable for constrained machines."""

    def __init__(self, database_path: Path, timeout_seconds: float = 30.0) -> None:
        self._database_path = database_path
        self._timeout_seconds = max(1.0, min(timeout_seconds, 120.0))

    def initialize(self) -> StorageResult:
        """Create the archive schema idempotently."""
        try:
            self._database_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                self._configure(connection)
                self._migrate(connection)
            return StorageResult(0, "Archive is ready.")
        except sqlite3.Error as error:
            logger.error("Archive initialization failed: {}", type(error).__name__)
            return StorageResult(0, "Archive initialization failed.", ok=False)

    def upsert(self, records: tuple[Publication, ...]) -> StorageResult:
        """Store records by stable identifier without duplicating a source record."""
        if not records:
            return StorageResult(0, "No records were provided for storage.")
        if not self.initialize().ok:
            return StorageResult(0, "Archive is unavailable.", ok=False)
        try:
            with self._connect() as connection:
                connection.executemany(
                    """
                    INSERT INTO publications (
                        identifier, title, abstract, source, source_url, doi, pmc_id,
                        authors_json, published_date, retrieved_at, topics_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(identifier) DO UPDATE SET
                        title=excluded.title, abstract=excluded.abstract, source=excluded.source,
                        source_url=excluded.source_url, doi=excluded.doi, pmc_id=excluded.pmc_id,
                        authors_json=excluded.authors_json,
                        published_date=excluded.published_date, retrieved_at=excluded.retrieved_at,
                        topics_json=excluded.topics_json
                    """,
                    tuple(self._row(record) for record in records),
                )
            return StorageResult(len(records), f"Stored {len(records)} record(s).")
        except sqlite3.Error as error:
            logger.error("Archive write failed: {}", type(error).__name__)
            return StorageResult(0, "Archive write failed.", ok=False)

    def recent(self, limit: int = 20) -> tuple[Publication, ...]:
        """Return most recently collected records, safely bounded by a caller limit."""
        bounded_limit = max(1, min(limit, 100))
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT identifier, title, abstract, source, source_url, doi, pmc_id,
                           authors_json, published_date, retrieved_at, topics_json
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
            return StorageResult(0, "Archive is unavailable.", ok=False)

    @contextmanager
    def _connect(self):
        """Yield a local connection and close it even when a query fails."""
        connection = sqlite3.connect(str(self._database_path), timeout=self._timeout_seconds)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute(f"PRAGMA busy_timeout={int(self._timeout_seconds * 1_000)}")
            connection.execute("PRAGMA foreign_keys=ON")
            yield connection
        except BaseException:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _configure(connection: sqlite3.Connection) -> None:
        """Enable local durability and bounded lock waits for concurrent readers and writers."""
        connection.execute("PRAGMA journal_mode=WAL")

    @staticmethod
    def _migrate(connection: sqlite3.Connection) -> None:
        """Apply idempotent schema updates and record the current schema version."""
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS publications (
                identifier TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                abstract TEXT NOT NULL,
                source TEXT NOT NULL,
                source_url TEXT NOT NULL,
                doi TEXT NOT NULL DEFAULT '',
                pmc_id TEXT NOT NULL DEFAULT '',
                authors_json TEXT NOT NULL,
                published_date TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                topics_json TEXT NOT NULL
            )
            """
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(publications)")}
        for name in ("doi", "pmc_id"):
            if name not in columns:
                connection.execute(
                    f"ALTER TABLE publications ADD COLUMN {name} TEXT NOT NULL DEFAULT ''"
                )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute(
            """
            INSERT INTO schema_metadata(key, value) VALUES ('schema_version', ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (_SCHEMA_VERSION,),
        )

    @staticmethod
    def _row(record: Publication) -> tuple[str, ...]:
        return (
            record.identifier,
            record.title,
            record.abstract,
            record.source,
            record.source_url,
            record.doi,
            record.pmc_id,
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
                "doi": row["doi"],
                "pmc_id": row["pmc_id"],
                "authors": json.loads(row["authors_json"]),
                "published_date": row["published_date"],
                "retrieved_at": row["retrieved_at"],
                "topics": json.loads(row["topics_json"]),
            }
        )
