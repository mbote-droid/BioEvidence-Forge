# Operations

## Local service

1. Copy `.env.example` to `.env` and set `BIOEVIDENCE_CONTACT_EMAIL` to a monitored
   address accepted by the source provider. Add `BIOEVIDENCE_NCBI_API_KEY` when available
   for higher documented request capacity.
2. Set `BIOEVIDENCE_TOPIC` in `.env` when using Compose.
3. Run `docker compose up --build -d`.
4. Open `http://127.0.0.1:8080/health` to confirm the review service is ready.
5. Reports are written to `reports/`; the SQLite archive is written to `data/`.
6. Use `docker compose logs -f collector` to inspect scheduled collection outcomes.
7. Use `docker compose down` for a controlled shutdown. The bind-mounted archive and
   reports remain on the host.

## Scheduling

The collector repeats after `BIOEVIDENCE_POLL_INTERVAL_MINUTES`. It waits through the
configured interval without busy looping, and the container restarts after a process
failure. Keep source request limits conservative to respect public endpoint policies.

## Archive maintenance

The SQLite archive enables WAL mode and a bounded busy timeout for a local API and
collector sharing one database. Avoid multiple collector containers against the same
archive. If a lock persists after a clean shutdown, make a backup, verify no process has
the database open, and restart the services. The schema metadata table records the local
archive version and applies compatible column additions automatically at startup.

## Backups and recovery

Back up the `data/` and `reports/` directories together. To recover, stop the services,
restore both directories, and start the services again. The source URL, retrieval time,
and identifiers remain embedded in the archive/report workflow for later review.
