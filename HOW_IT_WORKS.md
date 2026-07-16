# Runtime flow

1. An operator starts the command-line service, scheduler, or HTTP application.
2. Configuration is read from environment variables and validated into immutable settings.
3. A research topic is normalized and passed to the configured source connector.
4. The connector requests source records using documented public endpoints and bounded timeouts.
5. Returned payloads are parsed into validated publication records while retaining source URLs and timestamps.
6. Records are normalized, deduplicated by stable identifiers, and stored in the local SQLite database.
7. The scoring service assigns transparent relevance and evidence scores from record metadata.
8. The reporting service groups scored records into a Markdown evidence brief with citations and limitations.
9. The scheduler repeats this bounded workflow at its configured interval and records failures for later inspection.
10. The review interface exposes the resulting records and reports for human verification before any external use.

