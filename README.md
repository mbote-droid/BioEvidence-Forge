# BioEvidence Forge

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23267249.svg)](https://doi.org/10.5281/zenodo.23267249)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue?logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://github.com/mbote-droid/BioEvidence-Forge/actions/workflows/ci.yml/badge.svg)](https://github.com/mbote-droid/BioEvidence-Forge/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-96%25-brightgreen)](#quality)
[![Storage: SQLite](https://img.shields.io/badge/storage-SQLite-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org)
[![Offline-first](https://img.shields.io/badge/offline--first-no%20GPU-334155)](#design-commitments)

BioEvidence Forge is a self-hosted biomedical evidence monitor. It continuously collects open literature from
PubMed for the research topics you configure, stores every record with its provenance in a local SQLite archive,
scores relevance transparently, and writes review-ready Markdown evidence briefs with full citations.

```
topic ──► PubMed E-utilities ──► validated records ──► SQLite archive (WAL) ──► transparent scoring ──► Markdown brief
             (paced, retried)      (source URL, PMID,      (deduplicated,          (topic matches,         (citations,
                                    DOI, retrieval time)    versioned schema)        source, recency)        limitations)
```

## Design commitments

- **Offline-first.** Local SQLite storage; no GPU and no cloud services required.
- **Traceable.** Every record keeps its PMID, DOI, PMC ID, source URL and retrieval time.
- **Respectful collection.** Documented public endpoints only, paced at NCBI's published request rates, with bounded
  retries, exponential backoff and `Retry-After` support.
- **Fails safely.** Network errors, malformed responses and bad records become logged outcomes and an honest
  "collection failed" report, never a crash or a corrupt archive.
- **Secure by default.** Untrusted XML parsed with `defusedxml`; API bound to `127.0.0.1`; container runs unprivileged
  with a read-only filesystem and all Linux capabilities dropped.
- **Human in the loop.** Reports are evidence briefs for review, not conclusions; human review is mandatory before
  publication or clinical use.

## Components

| Module | Responsibility |
|---|---|
| `sources/pubmed.py` | ESearch + EFetch client with rate pacing, retries and defensive parsing |
| `models.py`, `validation.py` | Immutable, validated publication records from untrusted payloads |
| `storage.py` | SQLite archive with WAL mode, busy timeout, upserts and automatic schema migration |
| `scoring.py` | Transparent 0-100 score with stated factors (topic matches, indexed source, recency) |
| `reporting.py` | Markdown evidence briefs with citations and limitations |
| `pipeline.py`, `scheduler.py` | One bounded run, or repeated runs on an interval without busy-waiting |
| `api.py` | FastAPI review service: `GET /health`, `POST /runs`, `GET /publications` |
| `cli.py` | `bioevidence collect`, `bioevidence schedule`, `bioevidence health` |

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cp .env.example .env               # Windows: copy .env.example .env
# set BIOEVIDENCE_CONTACT_EMAIL in .env (NCBI asks for a contact address)

bioevidence health                 # check the archive
bioevidence collect "TP53 mutation africa"
pytest                             # 146 tests, 96% coverage gate
```

Review API:

```bash
uvicorn bioevidence.api:create_app --factory --host 127.0.0.1 --port 8080
curl http://127.0.0.1:8080/health
curl -X POST http://127.0.0.1:8080/runs -H "Content-Type: application/json" -d '{"topic": "sickle cell gene therapy"}'
```

## Continuous operation

Set `BIOEVIDENCE_CONTACT_EMAIL` and `BIOEVIDENCE_TOPIC` in `.env`, then:

```bash
docker compose up --build -d       # review API on 127.0.0.1:8080 plus a scheduled collector
docker compose logs -f collector
```

The archive (`data/`) and reports (`reports/`) are bind-mounted and survive restarts. See
[docs/OPERATIONS.md](docs/OPERATIONS.md) for scheduling, backups and recovery, and [HOW_IT_WORKS.md](HOW_IT_WORKS.md)
for the runtime flow.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `BIOEVIDENCE_CONTACT_EMAIL` | (empty) | Contact address sent to NCBI, as their usage guidance requests |
| `BIOEVIDENCE_NCBI_API_KEY` | (empty) | Optional key for a higher request rate |
| `BIOEVIDENCE_TOPIC` | general biomedical research | Topic for the scheduled collector |
| `BIOEVIDENCE_MAX_RESULTS` | 20 | Records per run (capped at 100) |
| `BIOEVIDENCE_POLL_INTERVAL_MINUTES` | 360 | Interval between scheduled runs |
| `BIOEVIDENCE_REQUEST_TIMEOUT_SECONDS` | 20 | HTTP timeout per request |
| `BIOEVIDENCE_DATABASE_PATH` | data/bioevidence.sqlite3 | SQLite archive location |
| `BIOEVIDENCE_REPORTS_PATH` | reports | Markdown brief directory |

## Quality

- 146 tests with a 95% branch-coverage gate (currently 96.5%), including network failures, HTTP 429 retries with `Retry-After`,
  malformed JSON and XML, articles without identifiers, XML entity-expansion attacks and legacy-schema
  migration.
- CI on Python 3.11, 3.12 and 3.13: ruff format and lint, pytest, bandit and pip-audit, plus a container build.
  Tagging a release publishes the image to GitHub Container Registry.

## Citation

Please cite using the metadata in [CITATION.cff](CITATION.cff).

## License

MIT © Samuel Mbote
