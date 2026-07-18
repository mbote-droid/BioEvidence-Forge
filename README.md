# BioEvidence Forge

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://github.com/mbote-droid/BioEvidence-Forge/actions/workflows/ci.yml/badge.svg)](https://github.com/mbote-droid/BioEvidence-Forge/actions/workflows/ci.yml)
[![Release](https://github.com/mbote-droid/BioEvidence-Forge/actions/workflows/release.yml/badge.svg)](https://github.com/mbote-droid/BioEvidence-Forge/actions/workflows/release.yml)
[![Storage: SQLite](https://img.shields.io/badge/storage-SQLite-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org)
[![Offline-first](https://img.shields.io/badge/offline--first-no%20GPU-334155)](#design-commitments)


BioEvidence Forge continuously collects open biomedical evidence, converts it into
traceable local records, prioritizes material against configured research topics,
and produces review-ready reports.

## Design commitments

- Offline-first local SQLite storage; no GPU is required.
- API-first collection with source URLs, retrieval times, and identifiers retained.
- Defensive validation at every boundary and safe, useful fallback output.
- Human review remains mandatory before publication or clinical use.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
bioevidence health
pytest
```

See [HOW_IT_WORKS.md](HOW_IT_WORKS.md) for the runtime flow and [docs/OPERATIONS.md](docs/OPERATIONS.md)
for scheduled operation.

## Continuous operation

Copy `.env.example` to `.env`, set your public-source contact email and research topic,
then run `docker compose up --build -d`. The collector runs on its configured schedule,
while the review service is available at `http://127.0.0.1:8080`.

The repository includes verification workflows for every push and pull request. Creating
a version tag publishes the verified container to the repository owner's GitHub Container
Registry namespace.
