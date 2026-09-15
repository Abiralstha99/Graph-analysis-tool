# MRG Labs Graphing API

The FastAPI backend listens locally on `http://localhost:8080`. Browser clients
use a secure session cookie, so authenticated requests must include credentials.

## Authentication

### `POST /register`

Creates an account.

```json
{
  "username": "lab-user",
  "password": "securepass1"
}
```

Passwords must contain at least eight characters and one digit. A successful
response is `{"status":"ok","username":"lab-user"}`.

### `POST /login`

Accepts the same JSON body as registration, verifies the credentials, and sets
the session cookie.

```json
{
  "status": "ok",
  "user_id": 1
}
```

### `POST /logout`

Clears the current session and returns `{"status":"ok"}`.

### `POST /change_password` (authenticated)

```json
{
  "current_password": "securepass1",
  "new_password": "newsecurepass2"
}
```

The new password follows the same strength rule as registration. A successful
response is `{"status":"ok","message":"Password updated successfully"}`.

### `GET /api/v1/files` (authenticated)

Returns the caller's saved graph records:

```json
{
  "files": [
    {
      "graph_id": 1,
      "baseline_filename": "baseline.csv",
      "sample_filename": "sample.csv",
      "generated_path": "/static/generated_graphs/sample.png",
      "created_at": "2026-09-14T12:00:00"
    }
  ]
}
```

The frontend also uses this protected route as its authentication probe.

## Health checks

| Method | Path | Auth | Purpose |
|---|---|:---:|---|
| `GET` | `/health` | No | Basic application liveness |
| `GET` | `/health/live` | No | Liveness probe |
| `GET` | `/health/ready` | No | Database readiness probe |
| `GET` | `/analysis/health` | No | Graph-analysis and Gemini configuration status |
| `GET` | `/chat/health` | No | Chat/Gemini status and persisted-session count |

`/health/ready` returns `200` with `{"status":"ok","db":"ok"}` on a
successful database check. It returns `503` with
`{"status":"degraded","db":"error"}` if the check fails.

## Persistent FTIR analysis jobs

The `/api/v1/analyses` routes validate uploads, queue background processing,
and persist analysis results in MySQL. All routes in this section require an
authenticated session.

### `POST /api/v1/analyses`

Creates a job and returns `202 Accepted`.

Content type: `multipart/form-data`

| Field | Type | Required | Notes |
|---|---|:---:|---|
| `baseline` | File | Yes | `.csv`, `.txt`, or `.dat`; maximum 10 MB |
| `samples` | File[] | Yes | At least one supported file; maximum 10 MB each |
| `scoring_method` | string | No | `hybrid`, `rmse`, `pearson`, or `area`; default `hybrid` |
| `zone_weights` | JSON string | No | Array of `{min, max, weight, label, key}` objects |

Files must have at least two finite numeric rows in their first two columns.
Parsing uses `header=1`, treating the first row as metadata.

```json
{
  "job_id": "c0a8012e-5a7b-4c5c-9b6c-0d7e0f7d4a12",
  "analysis_id": "0fcb8c34-0b9d-4a50-9f6b-cfcb4f4f9b2a",
  "status": "queued"
}
```

### `GET /api/v1/jobs/{job_id}`

Polls a job owned by the caller.

```json
{
  "job_id": "c0a8012e-5a7b-4c5c-9b6c-0d7e0f7d4a12",
  "status": "processing",
  "analysis_id": "0fcb8c34-0b9d-4a50-9f6b-cfcb4f4f9b2a",
  "error": null,
  "created_at": "2026-09-14T12:00:00",
  "updated_at": "2026-09-14T12:00:01"
}
```

Status is `queued`, `processing`, `completed`, `failed`, or `cancelled`.
Unexpected worker failures are retried up to three times; validation and parse
failures are non-retryable.

### `GET /api/v1/analyses`

Returns the caller's analyses. Query parameters `page` and `limit` default to
`1` and `20`, respectively; both must be positive.

```json
{
  "analyses": [
    {
      "analysis_id": "0fcb8c34-0b9d-4a50-9f6b-cfcb4f4f9b2a",
      "user_id": 1,
      "status": "completed",
      "baseline_filename": "baseline.csv",
      "sample_filenames": ["sample.csv"],
      "scoring_method": "hybrid",
      "scores": {"sample.csv": 87.4},
      "deviation_data": {
        "x": [4000, 3999],
        "deviation": [0.02, 0.01],
        "max_deviation": 0.02,
        "avg_deviation": 0.015
      },
      "summary": {"total": 1, "good": 0, "warning": 1, "critical": 0},
      "error": null,
      "created_at": "2026-09-14T12:00:00",
      "completed_at": "2026-09-14T12:00:01"
    }
  ],
  "pagination": {"page": 1, "limit": 20, "total": 1, "has_next": false}
}
```

### `GET /api/v1/analyses/{analysis_id}`

Returns one analysis owned by the caller. Before completion, `scores`,
`deviation_data`, `summary`, and `completed_at` are `null`.

### `DELETE /api/v1/analyses/{analysis_id}`

- Queued and processing analyses are marked `cancelled` and return `202` with
  the analysis response.
- Completed, failed, and cancelled analyses are deleted and return
  `204 No Content`.

## Direct FTIR routes

These existing synchronous routes require authentication.

### `POST /analysis/ftir/analyze`

Accepts `multipart/form-data` with `baseline`, `sample`, and optional
`sample_name`. It calculates summary statistics, generates a comparison image,
and requests Gemini analysis. The Gemini package, `GEMINI_API_KEY`, and
Matplotlib must be available.

```json
{
  "sample_name": "sample",
  "statistics": {
    "baseline_stats": {},
    "sample_stats": {},
    "differences": {}
  },
  "ai_insights": "...",
  "metadata": {
    "baseline_file": "baseline.csv",
    "sample_file": "sample.csv",
    "analysis_timestamp": "2026-09-14T12:00:00"
  }
}
```

### `POST /analysis/ftir/deviation`

Accepts `baseline`, `sample`, and optional `zone_weights` JSON. It returns
`success`, `deviationData`, `sampleInfo`, and `processingTime` in milliseconds.

### `POST /analysis/ftir/scores`

Accepts `baseline`, repeated `samples`, optional `scoring_method`, and optional
`zone_weights` JSON. It returns `success`, `scores`, aggregate
`deviationData`, a `summary` (`totalSamples`, `good`, `warning`, `critical`),
and `processingTime` in milliseconds.

### Unimplemented session routes

These routes currently return `501 Not Implemented`:

- `POST /analysis/ftir/sessions/save`
- `GET /analysis/ftir/sessions/history`

Other configuration, upload, and individual session paths referenced by the
frontend client are not registered by the backend.

## Chat routes

All chat routes except `/chat/health` require authentication.

### `POST /chat/send_message`

```json
{
  "message": "What does this peak shift suggest?",
  "conversation_history": [
    {"role": "user", "content": "...", "timestamp": "..."}
  ],
  "context": "Optional graph or dataset context"
}
```

The response includes `response`, `conversation_id`, `timestamp`, and a
`status` of `success`, `fallback`, or `fallback_error`. Successful responses
persist the two-message exchange in the `chat_sessions` table for the
authenticated user.

### `POST /chat/quick_question`

Accepts `{"question":"What is FTIR?"}` and returns the question, an answer,
a timestamp, and a status. It does not persist a conversation.

### `GET /chat/conversation/{conversation_id}`

Returns messages only when the conversation belongs to the authenticated user.

### `DELETE /chat/conversation/{conversation_id}`

Deletes the caller's persisted conversation and returns a confirmation.

## Graph export

### `POST /generate_graphs`

Accepts `multipart/form-data` with `baseline`, repeated `samples`, optional
`format` (`png` by default), `save_dir`, and `zip_filename`. The response is a
ZIP download containing generated comparison images.

## Errors and configuration

Application-level HTTP errors use this envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": {}
  }
}
```

Common codes include `VALIDATION_ERROR`, `WEAK_PASSWORD`, `UNAUTHORIZED`,
`FORBIDDEN`, `NOT_FOUND`, and `INTERNAL_ERROR`. The unimplemented FTIR session
routes retain their simple `{"error":"..."}` response.

Configuration is loaded at runtime from environment variables:

- `DB_HOST`, `DB_USER`, `DB_PASS` (or `DB_PASSWORD`), `DB_NAME`, `DB_PORT`
- `SESSION_SECRET` or `SECRET_KEY`
- `GEMINI_API_KEY`

Keep values in a local `.env` file or deployment secret store. Do not commit
or return secrets in API responses.

## Installation

```bash
cd backend
pip install -r requirements.txt
```

Run `backend/database_setup.sql` before using database-backed routes.
