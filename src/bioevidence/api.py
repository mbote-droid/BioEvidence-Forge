"""Local HTTP surface for triggering collection and reviewing retained records."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from bioevidence.config import Settings
from bioevidence.pipeline import ResearchPipeline
from bioevidence.reporting import ReportWriter
from bioevidence.sources.pubmed import PubMedClient
from bioevidence.storage import PublicationStore
from bioevidence.validation import safe_text


class TopicRequest(BaseModel):
    """Validated request body accepted by the collection endpoint."""

    topic: str = Field(default="general biomedical research", min_length=1, max_length=500)


def create_app(
    settings: Settings | None = None,
    pipeline: ResearchPipeline | None = None,
    store: PublicationStore | None = None,
) -> FastAPI:
    """Create a small local application with all services explicitly constructed."""
    runtime = settings or Settings.from_mapping()
    archive = store or PublicationStore(runtime.database_path)
    workflow = pipeline or ResearchPipeline(
        PubMedClient(
            contact_email=runtime.contact_email,
            timeout_seconds=runtime.request_timeout_seconds,
            max_results=runtime.max_results,
        ),
        archive,
        ReportWriter(runtime.reports_path),
    )
    application = FastAPI(title="BioEvidence Forge", version="0.1.0")

    @application.get("/health")
    def health() -> dict[str, object]:
        result = archive.count()
        return {"status": "ready", "records": result.count, "message": result.message}

    @application.post("/runs")
    def run_collection(request: TopicRequest) -> dict[str, object]:
        result = workflow.run(safe_text(request.topic, fallback="general biomedical research"))
        return {
            "topic": result.topic,
            "collected": result.collected,
            "stored": result.stored.count,
            "report_path": str(result.report.path) if result.report.path else None,
            "message": result.message,
        }

    @application.get("/publications")
    def publications(limit: int = 20) -> dict[str, object]:
        records = archive.recent(limit)
        return {
            "count": len(records),
            "records": [
                {
                    "identifier": record.identifier,
                    "title": record.title,
                    "source": record.source,
                    "source_url": record.source_url,
                    "citation": record.citation,
                }
                for record in records
            ],
        }

    return application
