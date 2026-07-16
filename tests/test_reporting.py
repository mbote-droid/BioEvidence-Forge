from bioevidence.models import Publication
from bioevidence.reporting import ReportWriter
from bioevidence.scoring import Score


def item():
    return Publication.from_mapping(
        {"identifier": "1", "title": "Evidence", "source": "PubMed", "source_url": "https://x"}
    )


class TestReporting:
    def test_write_creates_report(self, tmp_path):
        assert ReportWriter(tmp_path).write("topic", ()).path.exists()

    def test_empty_report_has_notice(self, tmp_path):
        assert "No eligible" in ReportWriter(tmp_path).write("topic", ()).path.read_text()

    def test_report_has_topic(self, tmp_path):
        assert "topic" in ReportWriter(tmp_path).write("topic", ()).path.read_text()

    def test_report_has_record_count(self, tmp_path):
        assert (
            ReportWriter(tmp_path).write("topic", ((item(), Score(1, ("x",))),)).record_count == 1
        )

    def test_report_has_title(self, tmp_path):
        assert (
            "Evidence"
            in ReportWriter(tmp_path).write("topic", ((item(), Score(1, ("x",))),)).path.read_text()
        )

    def test_report_has_score(self, tmp_path):
        assert (
            "1/100"
            in ReportWriter(tmp_path).write("topic", ((item(), Score(1, ("x",))),)).path.read_text()
        )

    def test_report_has_factors(self, tmp_path):
        assert (
            "x"
            in ReportWriter(tmp_path).write("topic", ((item(), Score(1, ("x",))),)).path.read_text()
        )

    def test_report_path_is_markdown(self, tmp_path):
        assert ReportWriter(tmp_path).write("topic", ()).path.suffix == ".md"

    def test_report_message_exists(self, tmp_path):
        assert ReportWriter(tmp_path).write("topic", ()).message

    def test_topic_is_escaped(self, tmp_path):
        assert "&lt;x&gt;" in ReportWriter(tmp_path).write("<x>", ()).path.read_text()
