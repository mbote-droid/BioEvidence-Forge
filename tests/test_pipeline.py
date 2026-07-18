from bioevidence.pipeline import ResearchPipeline
from bioevidence.reporting import ReportWriter
from bioevidence.sources.pubmed import SearchResult
from bioevidence.storage import PublicationStore


class Source:
    def __init__(self, result):
        self.result = result

    def search(self, topic):
        return self.result


class BrokenSource:
    def search(self, topic):
        raise RuntimeError("source unavailable")


class CloseableSource(Source):
    def close(self):
        return True


DEFAULT_RESULT = SearchResult((), "x", "Collected 0 record(s).")


def pipeline(tmp_path, result=DEFAULT_RESULT):
    return ResearchPipeline(
        Source(result), PublicationStore(tmp_path / "data.db"), ReportWriter(tmp_path / "reports")
    )


class TestPipeline:
    def test_run_has_topic(self, tmp_path):
        assert pipeline(tmp_path).run("topic").topic == "topic"

    def test_run_creates_report(self, tmp_path):
        assert pipeline(tmp_path).run("topic").report.path.exists()

    def test_run_has_message(self, tmp_path):
        assert pipeline(tmp_path).run("topic").message

    def test_empty_run_collects_zero(self, tmp_path):
        assert pipeline(tmp_path).run("topic").collected == 0

    def test_empty_run_stores_zero(self, tmp_path):
        assert pipeline(tmp_path).run("topic").stored.count == 0

    def test_blank_topic_falls_back(self, tmp_path):
        assert pipeline(tmp_path).run("").topic == "general biomedical research"

    def test_run_report_has_human_notice(self, tmp_path):
        assert "Human review" in pipeline(tmp_path).run("topic").report.path.read_text()

    def test_score_empty_is_empty(self):
        assert ResearchPipeline._score((), ("x",)) == ()

    def test_run_has_report_message(self, tmp_path):
        assert pipeline(tmp_path).run("topic").report.message

    def test_report_path_is_local(self, tmp_path):
        assert pipeline(tmp_path).run("topic").report.path.parent.name == "reports"

    def test_source_failure_is_safe(self, tmp_path):
        value = ResearchPipeline(
            BrokenSource(),
            PublicationStore(tmp_path / "data.db"),
            ReportWriter(tmp_path / "reports"),
        ).run("topic")
        assert "failed safely" in value.message

    def test_close_delegates_to_source(self, tmp_path):
        value = ResearchPipeline(
            CloseableSource(DEFAULT_RESULT),
            PublicationStore(tmp_path / "a.db"),
            ReportWriter(tmp_path),
        )
        assert value.close()
