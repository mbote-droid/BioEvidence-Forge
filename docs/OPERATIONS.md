# Operations

## Local service

1. Copy `.env.example` to `.env` and set `BIOEVIDENCE_CONTACT_EMAIL` to a monitored
   address accepted by the source provider.
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

## Backups and recovery

Back up the `data/` and `reports/` directories together. To recover, stop the services,
restore both directories, and start the services again. The source URL, retrieval time,
and identifiers remain embedded in the archive/report workflow for later review.

