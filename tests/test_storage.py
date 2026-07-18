import sqlite3
from datetime import UTC, datetime

from bioevidence.models import Publication
from bioevidence.storage import PublicationStore


def record(identifier="1"):
    return Publication.from_mapping(
        {"identifier": identifier, "title": "Title", "source": "PubMed", "source_url": "https://x"}
    )


class TestStorage:
    def test_initialize(self, tmp_path):
        assert PublicationStore(tmp_path / "a.db").initialize().message == "Archive is ready."

    def test_initialize_has_typed_success(self, tmp_path):
        assert PublicationStore(tmp_path / "a.db").initialize().ok

    def test_initialize_creates_file(self, tmp_path):
        store = PublicationStore(tmp_path / "a.db")
        store.initialize()
        assert (tmp_path / "a.db").exists()

    def test_upsert_count(self, tmp_path):
        assert PublicationStore(tmp_path / "a.db").upsert((record(),)).count == 1

    def test_count(self, tmp_path):
        store = PublicationStore(tmp_path / "a.db")
        store.upsert((record(),))
        assert store.count().count == 1

    def test_recent(self, tmp_path):
        store = PublicationStore(tmp_path / "a.db")
        store.upsert((record(),))
        assert store.recent()[0].identifier == "1"

    def test_empty_upsert(self, tmp_path):
        assert PublicationStore(tmp_path / "a.db").upsert(()).count == 0

    def test_upsert_deduplicates(self, tmp_path):
        store = PublicationStore(tmp_path / "a.db")
        store.upsert((record(),))
        store.upsert((record(),))
        assert store.count().count == 1

    def test_recent_limit_is_bounded(self, tmp_path):
        store = PublicationStore(tmp_path / "a.db")
        store.upsert((record("1"), record("2")))
        assert len(store.recent(1)) == 1

    def test_missing_archive_count_is_safe(self, tmp_path):
        assert PublicationStore(tmp_path / "none" / "a.db").count().count == 0

    def test_stored_authors(self, tmp_path):
        store = PublicationStore(tmp_path / "a.db")
        item = Publication.from_mapping({"identifier": "2", "authors": ["Ada"]})
        store.upsert((item,))
        assert store.recent()[0].authors == ("Ada",)

    def test_stored_doi_and_pmc_identifier(self, tmp_path):
        store = PublicationStore(tmp_path / "a.db")
        item = Publication.from_mapping({"identifier": "2", "doi": "10.1/x", "pmc_id": "PMC2"})
        store.upsert((item,))
        record = store.recent()[0]
        assert record.doi == "10.1/x" and record.pmc_id == "PMC2"

    def test_stored_retrieval_time_is_restored(self, tmp_path):
        store = PublicationStore(tmp_path / "a.db")
        timestamp = datetime(2020, 1, 1, tzinfo=UTC)
        store.upsert((Publication.from_mapping({"identifier": "2", "retrieved_at": timestamp}),))
        assert store.recent()[0].retrieved_at == timestamp

    def test_initialization_enables_wal(self, tmp_path):
        store = PublicationStore(tmp_path / "a.db")
        store.initialize()
        connection = sqlite3.connect(store._database_path)
        try:
            assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        finally:
            connection.close()

    def test_initialization_migrates_legacy_schema(self, tmp_path):
        path = tmp_path / "a.db"
        connection = sqlite3.connect(path)
        try:
            connection.execute("CREATE TABLE publications (identifier TEXT PRIMARY KEY)")
            connection.commit()
        finally:
            connection.close()
        store = PublicationStore(path)
        assert store.initialize().ok
        connection = sqlite3.connect(path)
        try:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(publications)")}
        finally:
            connection.close()
        assert {"doi", "pmc_id"}.issubset(columns)

    def test_directory_database_fails_initialization_safely(self, tmp_path):
        assert "failed" in PublicationStore(tmp_path).initialize().message.lower()

    def test_directory_database_fails_upsert_safely(self, tmp_path):
        assert PublicationStore(tmp_path).upsert((record(),)).count == 0

    def test_directory_database_fails_read_safely(self, tmp_path):
        assert PublicationStore(tmp_path).recent() == ()
