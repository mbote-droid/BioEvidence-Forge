from datetime import UTC, datetime

from bioevidence.models import Publication, utc_now


class TestModels:
    def test_now_is_timezone_aware(self):
        assert utc_now().tzinfo == UTC

    def test_mapping_default_identifier(self):
        assert Publication.from_mapping({}).identifier == "unknown"

    def test_mapping_default_title(self):
        assert Publication.from_mapping({}).title == "Unavailable"

    def test_mapping_retains_identifier(self):
        assert Publication.from_mapping({"identifier": "123"}).identifier == "123"

    def test_mapping_escapes_title(self):
        assert Publication.from_mapping({"title": "<b>"}).title == "&lt;b&gt;"

    def test_mapping_authors(self):
        assert Publication.from_mapping({"authors": ["One"]}).authors == ("One",)

    def test_mapping_rejects_non_sequence_authors(self):
        assert Publication.from_mapping({"authors": "One"}).authors == ()

    def test_mapping_topics(self):
        assert Publication.from_mapping({"topics": ["Genomics"]}).topics == ("genomics",)

    def test_citation_is_nonempty(self):
        assert Publication.from_mapping({}).citation

    def test_retrieved_at_is_aware(self):
        assert Publication.from_mapping({}).retrieved_at.tzinfo == UTC

    def test_mapping_retains_doi(self):
        assert Publication.from_mapping({"doi": "10.1000/example"}).doi == "10.1000/example"

    def test_mapping_restores_retrieved_at(self):
        timestamp = "2020-01-01T00:00:00+00:00"
        assert Publication.from_mapping({"retrieved_at": timestamp}).retrieved_at == datetime(
            2020, 1, 1, tzinfo=UTC
        )
