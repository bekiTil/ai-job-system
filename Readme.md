# Distributed AI Job Processing System

A horizontally scalable job processing system that accepts AI tasks (summarization, classification, entity extraction) via a REST API, queues them for asynchronous processing, and delivers results through a polling interface. Built with FastAPI, Celery, Redis, PostgreSQL, and Docker.

## Architecture

```
                         ┌─────────────────────────────────────────────────┐
                         │                Docker Network                   │
                         │                                                 │
Client ──▶ NGINX ──▶ ┌──┴──────────┐     ┌───────┐     ┌──────────────┐  │
           (LB)      │ API (×N)     │────▶│ Redis │◀────│ Workers (×N) │  │
                     │ FastAPI      │     │       │     │ Celery       │  │
                     └──┬───────────┘     └───────┘     └──────┬───────┘  │
                        │                                      │          │
                        │         ┌──────────────┐             │          │
                        └────────▶│  PostgreSQL   │◀────────────┘          │
                                  └──────────────┘                        │
                         └─────────────────────────────────────────────────┘
```

**Request flow:** A client submits a job to the API through NGINX. The API validates the request, stores the job in PostgreSQL with status "pending," pushes it onto the Redis queue, and returns immediately. A Celery worker picks up the job, calls the AI model (or simulation), writes the result to PostgreSQL, and caches it in Redis. The client polls for the result.

## What It Does

The system processes three types of AI tasks:

- **Summarize** — condenses text into a 2-3 sentence summary
- **Classify** — categorizes text by type, sentiment, and key topics
- **Extract** — pulls out named entities (people, organizations, locations, dates)

Processing uses the Anthropic Claude API when a key is provided, otherwise falls back to a simulation for development and testing.

## How It Scales

Every component is stateless and independently scalable:

- **API containers** — NGINX round-robins requests across N instances. Adding more handles higher request throughput.
- **Worker containers** — each pulls from the same Redis queue. Adding more increases job processing parallelism. 5 workers process 5 jobs simultaneously.
- **Redis** — serves three roles using separate databases: message broker (db 0), result cache and rate limiter (db 1).
- **PostgreSQL** — single shared database for job state and results.

Scaling requires no code changes:

```bash
docker-compose up --build --scale api=3 --scale worker=5
```

## Reliability Features

- **Automatic retries** — failed jobs retry up to 3 times with exponential backoff (5s, 10s, 20s)
- **Time limits** — soft limit at 25s triggers a retry, hard limit at 30s kills the task
- **Stale job recovery** — a checker requeues jobs stuck in "running" for over 60 seconds
- **Idempotency** — workers check if a job is already completed before processing
- **Permanent failure tracking** — after all retries are exhausted, the failure reason is recorded in the database

## Protection Mechanisms

- **Rate limiting** — 10 requests per minute per user (HTTP 429)
- **Backpressure** — rejects new jobs when the queue exceeds 1000 pending items (HTTP 503)
- **Result caching** — identical requests served from Redis cache (1-hour TTL) to avoid redundant AI calls

## Observability

- **Structured JSON logging** — all services output machine-parseable JSON logs
- **Metrics** — job counts, processing durations, HTTP request stats tracked in Redis
- **`/dashboard` endpoint** — computed error rates, average processing times, and throughput
- **`/health` endpoint** — quick liveness check

## Project Structure

```
ai-job-system/
├── app/
│   ├── ai_client.py          # Anthropic Claude API client
│   ├── celery_app.py          # Celery configuration
│   ├── dashboard.py           # Computed metrics endpoint
│   ├── database.py            # SQLAlchemy engine & session
│   ├── logging_config.py      # JSON logging setup
│   ├── main.py                # FastAPI endpoints
│   ├── metrics.py             # Redis-based metrics
│   ├── middleware.py           # Request logging middleware
│   ├── models.py              # User and Job models
│   ├── processing.py          # AI processing logic
│   ├── redis_client.py        # Redis client
│   ├── schemas.py             # Pydantic schemas
│   ├── stale_checker.py       # Stuck job recovery
│   └── tasks.py               # Celery task with retries
├── alembic/                   # Database migrations
├── Dockerfile.api
├── Dockerfile.worker
├── docker-compose.yml
├── nginx.conf
├── start.sh                   # Migrations + API startup
├── requirements.txt
└── stress_test.py
```

## Getting Started

### Prerequisites

Docker and Docker Compose.

### Run

```bash
docker-compose up --build
```

Starts PostgreSQL, Redis, the API, a worker, and NGINX. Migrations run automatically. The API is available at `http://localhost`.

### With Claude AI

```bash
export ANTHROPIC_API_KEY=your-key-here
docker-compose up --build
```

Without a key, processing uses a 3-second simulation.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/users` | Create a user |
| POST | `/jobs` | Submit a job |
| GET | `/jobs/{id}` | Get job status and result |
| GET | `/jobs?user_id={id}` | List jobs for a user |
| GET | `/health` | Liveness check |
| GET | `/metrics` | Raw metrics |
| GET | `/dashboard` | Computed system stats |

### Example

```bash
# Create a user
curl -X POST http://localhost/users \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "name": "Test User"}'

# Submit a job (returns immediately)
curl -X POST http://localhost/jobs \
  -H "Content-Type: application/json" \
  -d '{"user_id": "USER_ID", "task_type": "summarize", "input_text": "Your text here..."}'

# Poll for result
curl http://localhost/jobs/JOB_ID
```

## Tech Stack

FastAPI, Celery, Redis, PostgreSQL, SQLAlchemy, Alembic, NGINX, Docker, Anthropic Claude API
