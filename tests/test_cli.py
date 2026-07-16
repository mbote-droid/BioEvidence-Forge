from bioevidence.cli import build_pipeline, main, parse_args
from bioevidence.config import Settings


class TestCli:
    def test_collect_command(self):
        assert parse_args(["collect"]).command == "collect"

    def test_schedule_command(self):
        assert parse_args(["schedule"]).command == "schedule"

    def test_health_command(self):
        assert parse_args(["health"]).command == "health"

    def test_collect_topic(self):
        assert parse_args(["collect", "genomics"]).topic == "genomics"

    def test_schedule_topic(self):
        assert parse_args(["schedule", "oncology"]).topic == "oncology"

    def test_collect_default_topic(self):
        assert parse_args(["collect"]).topic == "general biomedical research"

    def test_schedule_default_topic(self):
        assert parse_args(["schedule"]).topic == "general biomedical research"

    def test_collect_has_command_attribute(self):
        assert hasattr(parse_args(["collect"]), "command")

    def test_health_has_command_attribute(self):
        assert hasattr(parse_args(["health"]), "command")

    def test_commands_are_distinct(self):
        assert parse_args(["collect"]).command != parse_args(["health"]).command

    def test_build_pipeline(self, tmp_path):
        settings = Settings.from_mapping({"BIOEVIDENCE_DATABASE_PATH": str(tmp_path / "a.db")})
        assert build_pipeline(settings)

    def test_health_main(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BIOEVIDENCE_DATABASE_PATH", str(tmp_path / "a.db"))
        assert main(["health"]) == 0
