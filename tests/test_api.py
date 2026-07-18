from fastapi.testclient import TestClient

from bioevidence.api import create_app
from bioevidence.config import Settings
from bioevidence.pipeline import RunResult
from bioevidence.reporting import ReportResult
from bioevidence.storage import PublicationStore, StorageResult


class Workflow:
    def __init__(self):
        self.topics = []
        self.closed = False

    def run(self, topic):
        self.topics.append(topic)
        return RunResult(topic, 0, StorageResult(0, "x"), ReportResult(None, 0, "x"), "completed")

    def close(self):
        self.closed = True
        return True


def client(tmp_path):
    settings = Settings.from_mapping({"BIOEVIDENCE_DATABASE_PATH": str(tmp_path / "data.db")})
    store = PublicationStore(settings.database_path)
    workflow = Workflow()
    return TestClient(create_app(settings, workflow, store)), workflow


class TestApi:
    def test_health_is_ready(self, tmp_path):
        assert client(tmp_path)[0].get("/health").json()["status"] == "ready"

    def test_health_has_count(self, tmp_path):
        assert "records" in client(tmp_path)[0].get("/health").json()

    def test_collection_is_successful(self, tmp_path):
        assert client(tmp_path)[0].post("/runs", json={"topic": "genomics"}).status_code == 200

    def test_collection_has_topic(self, tmp_path):
        assert (
            client(tmp_path)[0].post("/runs", json={"topic": "genomics"}).json()["topic"]
            == "genomics"
        )

    def test_collection_calls_workflow(self, tmp_path):
        value, workflow = client(tmp_path)
        value.post("/runs", json={"topic": "genomics"})
        assert workflow.topics == ["genomics"]

    def test_collection_has_message(self, tmp_path):
        assert (
            client(tmp_path)[0].post("/runs", json={"topic": "x"}).json()["message"] == "completed"
        )

    def test_collection_rejects_blank_topic(self, tmp_path):
        assert client(tmp_path)[0].post("/runs", json={"topic": ""}).status_code == 422

    def test_publications_returns_list(self, tmp_path):
        assert client(tmp_path)[0].get("/publications").json()["records"] == []

    def test_publications_has_count(self, tmp_path):
        assert client(tmp_path)[0].get("/publications").json()["count"] == 0

    def test_publications_accepts_limit(self, tmp_path):
        assert client(tmp_path)[0].get("/publications?limit=1").status_code == 200

    def test_lifespan_closes_workflow(self, tmp_path):
        value, workflow = client(tmp_path)
        with value:
            assert not workflow.closed
        assert workflow.closed
