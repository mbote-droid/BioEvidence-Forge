from bioevidence.models import Publication
from bioevidence.storage import PublicationStore


def record(identifier="1"):
    return Publication.from_mapping(
        {"identifier": identifier, "title": "Title", "source": "PubMed", "source_url": "https://x"}
    )


class TestStorage:
    def test_initialize(self, tmp_path):
        assert PublicationStore(tmp_path / "a.db").initialize().message == "Archive is ready."

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

    def test_directory_database_fails_initialization_safely(self, tmp_path):
        assert "failed" in PublicationStore(tmp_path).initialize().message.lower()

    def test_directory_database_fails_upsert_safely(self, tmp_path):
        assert PublicationStore(tmp_path).upsert((record(),)).count == 0

    def test_directory_database_fails_read_safely(self, tmp_path):
        assert PublicationStore(tmp_path).recent() == ()
