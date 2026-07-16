# BioEvidence Forge

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

