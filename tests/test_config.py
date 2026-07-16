from pathlib import Path

from bioevidence.config import Settings, _positive_int


class TestConfig:
    def test_default_database_path(self):
        assert Settings.from_mapping({}).database_path == Path("data/bioevidence.sqlite3")

    def test_default_reports_path(self):
        assert Settings.from_mapping({}).reports_path == Path("reports")

    def test_reads_database_path(self):
        assert Settings.from_mapping({"BIOEVIDENCE_DATABASE_PATH": "x.db"}).database_path == Path(
            "x.db"
        )

    def test_reads_contact_email(self):
        assert (
            Settings.from_mapping({"BIOEVIDENCE_CONTACT_EMAIL": " a@b.test "}).contact_email
            == "a@b.test"
        )

    def test_reads_timeout(self):
        assert (
            Settings.from_mapping(
                {"BIOEVIDENCE_REQUEST_TIMEOUT_SECONDS": "9"}
            ).request_timeout_seconds
            == 9
        )

    def test_invalid_timeout_defaults(self):
        assert (
            Settings.from_mapping(
                {"BIOEVIDENCE_REQUEST_TIMEOUT_SECONDS": "no"}
            ).request_timeout_seconds
            == 20
        )

    def test_zero_timeout_defaults(self):
        assert _positive_int("0", 4) == 4

    def test_negative_value_defaults(self):
        assert _positive_int("-4", 4) == 4

    def test_reads_max_results(self):
        assert Settings.from_mapping({"BIOEVIDENCE_MAX_RESULTS": "3"}).max_results == 3

    def test_reads_poll_interval(self):
        assert (
            Settings.from_mapping({"BIOEVIDENCE_POLL_INTERVAL_MINUTES": "12"}).poll_interval_minutes
            == 12
        )
