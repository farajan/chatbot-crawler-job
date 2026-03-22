# Chatbot Crawler Job

Kubernetes Job that crawls a website and stores pages in PostgreSQL. Created programmatically by a Spring Boot backend via the K8s API.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CRAWL_JOB_ID` | yes | — | UUID of the crawl job to execute |
| `MAX_DEPTH` | no | `5` | Maximum crawl depth |
| `MAX_PAGES` | no | `2000` | Maximum number of pages to crawl |
| `DB_HOST` | no | `127.0.0.1` | PostgreSQL host (K8s ConfigMap) |
| `DB_PORT` | no | `5432` | PostgreSQL port |
| `DB_NAME` | no | `chatbot` | Database name |
| `DB_USER` | no | `chatbot` | Database user |
| `DB_PASSWORD` | no | `postgres` | Database password (K8s Secret) |

## Local Run

Defaults are in `.env.localhost` — no manual env setup needed:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

## Docker

```bash
docker build -t chatbot-crawler-job .
docker run --rm \
  -e CRAWL_JOB_ID=<uuid> \
  -e DB_HOST=host.docker.internal \
  --shm-size=256m \
  chatbot-crawler-job
```

## Kubernetes

The Spring Boot backend creates a K8s Job with this image. Configuration sources:

- **ConfigMap** — `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`
- **Secret** (`secretKeyRef`) — `DB_PASSWORD`
- **Job spec** (per execution) — `CRAWL_JOB_ID`, `MAX_DEPTH`, `MAX_PAGES`
- Mount `/dev/shm` as `emptyDir` with `medium: Memory` for Chromium stability
- `backoffLimit` controls retry behavior (exit code 0 = success, non-zero = failure)
