# Matchday

A personal résumé and job-description analyzer with a scheduled remote-job shortlist.

## Run locally

Requires Python 3.12 or newer and outbound HTTPS access to `remotive.com`.

```sh
cd /workspace/ATS_matchmaker
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python server.py
```

The server listens on loopback port 5000. `HOST`, `PORT`, and `ATS_DB` can override the bind address, port, and database path. In the prepared cloud workspace, use `/workspace/ats-venv/bin/python server.py`.

1. Upload a text-based PDF or UTF-8 TXT CV (maximum 3 MB, 30 PDF pages).
2. Set optional title/location filters, the shortlist size, maximum age, and minimum recognized skill coverage. Save preferences before searching.
3. Run a search manually to verify the job source.
4. Enable the daily agent and save preferences.

Defaults: **up to 5 jobs**, posted within **15 days**, at **09:00 EST (fixed UTC−5)**, with at least **70% recognized skill coverage**. Choose “Eastern · DST auto” if you mean New York local time with daylight saving instead of fixed EST. No geographic restriction is assumed; the current source provides remote jobs only. The supplied LinkedIn URL is profile metadata; the app does not scrape LinkedIn or retrieve a CV from it.

## Scheduling and deployment

`server.py` starts Waitress and one scheduler thread. Keep exactly one server instance running. The scheduler checks every 30 seconds and persists one automatic attempt per local date. Starting after the scheduled time triggers that day's search; missed previous days are not replayed. Failed automatic searches are shown in the dashboard and can be retried manually. Saving new preferences after today's automatic attempt takes effect for the next automatic day; manual search uses saved preferences immediately.

An open browser is not required, but an **always-on server is required**. A temporary coding session is not a dependable daily host. Results are stored in this dashboard; no email notifications or external calendar events are created.

For a machine with Docker Compose:

```sh
docker compose up --build -d
```

The compose file binds only to host loopback, uses a persistent named volume, and restarts the process after failures/reboots while Docker is running. The Docker build is provided but has not been validated in the cloud workspace. This is a single-user application without sign-in. To access it remotely, use a private tunnel or an authenticated HTTPS reverse proxy; do not expose an unauthenticated public port. Back up the volume/database if results need to survive host replacement. Deployment and hosting are not provisioned by this repository.

## Matching and data limits

- Public listings come from the Remotive API and are cached for 15 minutes. Original source links and attribution are included.
- Jobs must have a valid posting date no older than the configured age, a matching title/location filter, and the configured skill coverage. Future dates are rejected.
- Coverage is recognized CV/job skill overlap divided by recognized job skills. It is an explainable keyword baseline, **not an AI semantic judgment, hiring probability, or actual ATS score**. The vocabulary is defined in `app.py`; skills outside it are not scored. Review seniority, eligibility, salary, and full job requirements before applying.
- Role filters require all entered words in the job title. Location filters use substring matching, with worldwide listings always eligible. Different source naming can require adjusting the filter.
- Fewer than five listings may qualify. The app never invents listings to reach the requested count, and does not claim complete coverage of LinkedIn or the job market.
- Scanned PDFs need OCR before upload. Uploaded CV text stays in the local SQLite database and is not sent to Remotive. Delete résumé removes the stored text, metadata, and results and pauses automation; this is logical database deletion, not a secure erasure guarantee for backups or disk.
- The cloud environment initially blocked `remotive.com` with a proxy HTTP 403. Allow this domain in environment settings before attempting live searches. A source outage preserves the previous shortlist and returns a visible error.

## Validation

```sh
/workspace/ats-venv/bin/python -m unittest discover -s tests -v
/workspace/ats-venv/bin/pip check
node --check static/app.js
```

Tests cover date boundaries, ranking, counts, location/title filters, upload/analysis/deletion, input validation, source failures and caching, cross-origin writes, and daily EST scheduling. Source tests use fixtures rather than fabricated live results.
