# Engineering Plan — MRG Labs Graphing App

Two engineers split the work below. Before either person writes a line of feature code, both must agree on the
contracts in the **Shared Contracts** section.

---

## Table of Contents

1. [Shared Contracts](#shared-contracts)
   - [API Contract](#api-contract)
   - [Database Schema](#database-schema)
   - [Folder Structure](#folder-structure)
   - [Error Envelope](#error-envelope)
2. [Fix-Before-Features Checklist](#fix-before-features-checklist)
3. [Person 1 — Core Analysis Path](#person-1--core-analysis-path)
4. [Person 2 — Infrastructure Around It](#person-2--infrastructure-around-it)
5. [Integration Point](#integration-point)
6. [CI/CD](#cicd)
7. [Recommended Build Order](#recommended-build-order)

---

## Shared Contracts

### API Contract

| Method   | Path                              | Auth required | Description                                    |
|----------|-----------------------------------|:-------------:|------------------------------------------------|
| `POST`   | `/api/v1/analyses`                | ✅            | Upload baseline + samples, create analysis job |
| `GET`    | `/api/v1/analyses`                | ✅            | List user's analyses (paginated)               |
| `GET`    | `/api/v1/analyses/{analysis_id}`  | ✅            | Fetch single analysis result                   |
| `DELETE` | `/api/v1/analyses/{analysis_id}`  | ✅            | Delete owned analysis                          |
| `GET`    | `/api/v1/jobs/{job_id}`           | ✅            | Poll async job status                          |
| `GET`    | `/health/live`                    | ❌            | Liveness probe                                 |
| `GET`    | `/health/ready`                   | ❌            | Readiness probe (DB ping, no credentials)      |

#### `POST /api/v1/analyses` — request (`multipart/form-data`)

| Field           | Type        | Required | Notes                                        |
|-----------------|-------------|:--------:|----------------------------------------------|
| `baseline`      | `File`      | ✅       | `.csv`, `.txt`, or `.dat`; max 10 MB         |
| `samples`       | `File[]`    | ✅       | 1–20 supported files, max 10 MB each         |
| `scoring_method`| `string`    | ❌       | `hybrid` \| `rmse` \| `pearson` \| `area`, default `hybrid` |
| `zone_weights`  | JSON string | ❌       | Array of `{min, max, weight, label, key}`    |

#### `POST /api/v1/analyses` — response `202 Accepted`

```json
{
  "job_id": "uuid",
  "analysis_id": "uuid",
  "status": "queued"
}
```

#### `GET /api/v1/jobs/{job_id}` — response `200`

```json
{
  "job_id": "uuid",
  "status": "queued | processing | completed | failed | cancelled",
  "analysis_id": "uuid | null",
  "error": "string | null",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

#### `GET /api/v1/analyses/{analysis_id}` — response `200`

This endpoint always returns the analysis shape below. For incomplete or
failed analyses, `scores`, `deviation_data`, `summary`, and `completed_at` are
`null`; clients poll `/api/v1/jobs/{job_id}` for job progress.

```json
{
  "analysis_id": "uuid",
  "user_id": 1,
  "status": "completed",
  "baseline_filename": "baseline.csv",
  "sample_filenames": ["s1.csv", "s2.csv"],
  "scoring_method": "hybrid",
  "scores": { "s1.csv": 87.4, "s2.csv": 63.1 },
  "deviation_data": {
    "x": [4000, 3999],
    "deviation": [0.02, 0.01],
    "max_deviation": 0.45,
    "avg_deviation": 0.12
  },
  "summary": { "total": 2, "good": 1, "warning": 0, "critical": 1 },
  "created_at": "ISO8601",
  "completed_at": "ISO8601"
}
```

#### `DELETE /api/v1/analyses/{analysis_id}`

- `queued` and `processing` analyses and their jobs are marked `cancelled` and
  return `202` with the analysis response shape.
- `completed`, `failed`, and `cancelled` analyses are physically deleted and
  return `204 No Content`.

#### `GET /api/v1/analyses` — response `200`

```json
{
  "analyses": [ /* same shape as GET /analyses/{id} */ ],
  "pagination": { "page": 1, "limit": 20, "total": 42, "has_next": true }
}
```

#### Canonical error envelope (all 4xx / 5xx)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": {}
  }
}
```

`detail=str(e)` is **never** used anywhere.

---

### Database Schema

Add to `backend/database_setup.sql`:

```sql
-- analyses: one row per analysis request
CREATE TABLE analyses (
    id                CHAR(36)     PRIMARY KEY,   -- UUID
    user_id           INT          NOT NULL,
    scoring_method    VARCHAR(20)  NOT NULL DEFAULT 'hybrid',
    zone_weights      JSON,
    status            ENUM('queued','processing','completed','failed','cancelled')
                                   NOT NULL DEFAULT 'queued',
    baseline_filename VARCHAR(255),
    sample_filenames  JSON,                        -- ["s1.csv", "s2.csv"]
    scores            JSON,                        -- {"s1.csv": 87.4}
    deviation_data    JSON,
    summary           JSON,                        -- {good, warning, critical}
    error_message     TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at      TIMESTAMP NULL,
    INDEX idx_analyses_user_id   (user_id),
    INDEX idx_analyses_status    (status),
    INDEX idx_analyses_created_at(created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- jobs: async job tracking
CREATE TABLE jobs (
    id            CHAR(36)    PRIMARY KEY,   -- UUID
    analysis_id   CHAR(36)    NOT NULL,
    user_id       INT         NOT NULL,
    status        ENUM('queued','processing','completed','failed','cancelled')
                              NOT NULL DEFAULT 'queued',
    attempt       INT         NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_jobs_analysis_id (analysis_id),
    INDEX idx_jobs_user_id     (user_id),
    INDEX idx_jobs_status      (status),
    FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)     REFERENCES users(id)    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- chat_sessions: persisted chat history per authenticated user
CREATE TABLE chat_sessions (
    id         VARCHAR(64) PRIMARY KEY,
    user_id    INT         NOT NULL,
    messages   JSON        NOT NULL,
    created_at TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_chat_sessions_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### Folder Structure

New files only (existing files stay in place):

```
backend/
  routers/
    analyses.py          ← Person 1: GET / DELETE / list endpoints
    jobs.py              ← Person 2: job status endpoint
    health.py            ← Person 2: /health/live + /health/ready
    auth.py              ← Person 2: move existing auth routes here
  services/
    analysis_service.py  ← Person 1: validate → parse → score → persist
    job_service.py       ← Person 2: create / update / query jobs
    auth_service.py      ← Person 2: rate limiting, password rules
    chat_session_service.py ← Person 2: persist chat_sessions rows
  schemas/
    analysis.py          ← Person 1: Pydantic request/response models
    job.py               ← Person 2: Pydantic job models
    error.py             ← shared: canonical error envelope
  middleware/
    logging.py           ← Person 2: request_id, duration_ms structured log
    auth.py              ← Person 2: require_auth dependency
  tests/
    test_analyses.py     ← Person 1: route integration tests
    test_jobs.py         ← Person 2: job integration tests
    test_auth.py         ← Person 2: auth integration tests
```

---

### Error Envelope

`backend/schemas/error.py` — defined once, used everywhere:

```python
from pydantic import BaseModel

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = {}

class ErrorResponse(BaseModel):
    error: ErrorDetail
```

Register a global exception handler in `app.py` that converts every `HTTPException`
into this shape. No route handler may return a raw exception string.

---

## Fix-Before-Features Checklist

Both engineers complete these before any new feature work.

| # | Fix | Owner |
|---|-----|-------|
| 1 | Route mismatch: frontend calls `/analysis/ftir/analyze`, backend exposes `/analysis/generate_insights` — rename the backend route and update `ftirApi.ts` | Person 1 |
| 2 | Fix the failing frontend download test in `fileSystemAccess.test.ts` | Person 1 |
| 3 | Delete the 200-line commented-out `generate_graphs` block in `app.py` (lines 180–242) | Either |
| 4 | Replace every `detail=str(e)` with the canonical error envelope | Person 2 |
| 5 | Move hardcoded `http://localhost:5000` in `frontend/src/services/api.ts` into a Vite env var | Person 1 |
| 6 | Add `Depends(require_auth)` to `/api/v1/files` and all analysis and chat routes | Person 2 |
| 7 | Chat `conversation_store` is an in-memory dict — Person 2 migrates it to a `chat_sessions` DB table as part of auth hardening | Person 2 |
| 8 | Update `README.md` and OpenAPI title to reflect actual routes after all of the above | Both |

---

## Person 1 — Core Analysis Path

**Owns:** `analysis_service.py`, `routers/analyses.py`, `schemas/analysis.py`,
`tests/test_analyses.py`, and the route rename fix.

### Tasks (in order)

#### 1. Fix the route mismatch

The frontend `FTIRApiService` calls:

- `POST /analysis/ftir/analyze`
- `POST /analysis/ftir/deviation`
- `POST /analysis/ftir/scores`
- `POST /analysis/ftir/sessions/save`
- `GET  /analysis/ftir/sessions/history`

The backend exposes only `POST /analysis/generate_insights`.

**Action:** In `backend/graph_analysis.py`, rename
`@router.post("/generate_insights")` → `@router.post("/ftir/analyze")` and add
stub 501 routes for the remaining paths so the frontend stops 404-ing. Fully
implement them in step 4 below.

#### 2. Write `schemas/analysis.py`

Pydantic models matching the agreed contract. Use `model_validator` to reject
empty sample lists and unknown scoring methods. Every response model must be
importable by the router and by tests.

#### 3. Write `services/analysis_service.py`

One public method — this is the exact signature Person 2's job worker calls:

```python
class AnalysisService:
    def run(
        self,
        baseline_bytes: bytes,
        baseline_name: str,
        samples: list[tuple[bytes, str]],   # [(file_bytes, filename), ...]
        scoring_method: str,
        zone_weights: list[dict] | None,
        analysis_id: str,
        db_conn,
    ) -> None:
        # 1. Validate (size ≤ 10 MB, extension .csv/.txt/.dat,
        #             row count ≥ 2, two numeric columns)
        # 2. Parse CSVs using existing process_file logic
        # 3. Align x-axes (inner join on wavenumber)
        # 4. Score using ported RMSE / Pearson / area / hybrid methods
        # 5. Build deviation_data and summary
        # 6. Write results into the analyses table
        # raises AnalysisError subclass on any failure
```

Port the scoring logic from
`frontend/src/features/analysis/lib/ftirAnalysis.ts` (lines 248–387) to Python
using `numpy`. All three methods (RMSE, Pearson, area) plus the hybrid
combination are pure math with no DOM dependencies.

#### Required analysis data flow

The backend is the authoritative owner of all graph calculations. The
frontend sends the baseline and sample data, receives the calculated results,
and only renders the graph and scores.

```text
Frontend
  ↓
send baseline + sample(s)
  ↓
Backend
  ├─ calculate deviation
  ├─ calculate weighted deviation
  ├─ calculate RMSE
  ├─ calculate Pearson
  ├─ calculate area difference
  └─ calculate hybrid score
  ↓
return results
  ↓
Frontend renders graph + scores
```

The frontend must not calculate authoritative deviation data or scores. Any
client-side calculations used for interaction or preview must not replace the
backend response or be persisted as analysis results.

#### 4. Write `routers/analyses.py`

Wire the four CRUD endpoints. Every route must:

- Call `require_auth` (Person 2's dependency) to get `user_id`
- Use `AnalysisService` and `JobService` (Person 2)
- Return the agreed response shapes
- Use the canonical error envelope on failure

`POST /api/v1/analyses`:
1. Read multipart files into memory
2. Insert a `queued` row into `analyses`
3. Call `job_service.create_job(analysis_id, user_id, db)`
4. Enqueue a `BackgroundTask` calling `job_service.run_job(...)`
5. Return 202 with `{job_id, analysis_id, status: "queued"}`

#### 5. Add new tables to `database_setup.sql`

Copy the two `CREATE TABLE` statements from the **Database Schema** section above.

#### 6. Write `tests/test_analyses.py`

Use FastAPI `TestClient` with mocked DB and mocked `AnalysisService.run`.

| Test | Expected |
|------|----------|
| `POST` with valid CSV files | 202, `job_id` returned |
| `GET /analyses` | returns only requesting user's analyses |
| `GET /analyses/{id}` with wrong user | 403 |
| `DELETE /analyses/{id}` | row removed |
| `POST` with non-CSV file | 422 with `code: "VALIDATION_ERROR"` |
| `POST` unauthenticated | 401 |
| `POST` with empty samples list | 422 |

---

## Person 2 — Infrastructure Around It

**Owns:** `job_service.py`, `routers/jobs.py`, `routers/health.py`,
`routers/auth.py`, `middleware/logging.py`, `middleware/auth.py`,
`schemas/job.py`, `schemas/error.py`, `tests/test_jobs.py`, `tests/test_auth.py`.

### Tasks (in order)

#### 1. Write `schemas/error.py`

The canonical error envelope (see **Error Envelope** above). Register the global
`HTTPException` handler in `app.py` immediately. This unblocks Person 1 from
removing `detail=str(e)` calls.

#### 2. Write `middleware/auth.py`

FastAPI dependency `require_auth(request: Request) -> int` that returns
`user_id` from the session or raises a 401 using the error envelope. Replaces
the existing `get_current_user_id` in `app.py` — update every caller.

#### 3. Write `services/job_service.py`

```python
def create_job(analysis_id: str, user_id: int, db) -> str:
    # insert job row with status='queued', return job_id (UUID)

def run_job(job_id: str, analysis_service: AnalysisService, db) -> None:
    # set status='processing'
    # call analysis_service.run(...)
    # on success: set status='completed' on both jobs and analyses rows
    # on AnalysisError / Exception: set status='failed', store sanitized message
    # max 3 attempts with exponential backoff (time.sleep)

def get_job(job_id: str, user_id: int, db) -> dict:
    # fetch row; if job.user_id != user_id raise 403
```

Use FastAPI `BackgroundTasks` as the queue for now (no Redis required yet).

#### 4. Write `routers/jobs.py`

`GET /api/v1/jobs/{job_id}`:
- Call `require_auth` → `user_id`
- Call `job_service.get_job(job_id, user_id, db)` (ownership enforced inside)
- Return agreed job shape or 404 / 403

#### 5. Write `routers/health.py`

- `GET /health/live` → always `{"status": "ok"}` (200)
- `GET /health/ready` → run `SELECT 1` against DB:
  - success → `{"status": "ok", "db": "ok"}` (200)
  - failure → `{"status": "degraded", "db": "error"}` (503)
  - **Never** expose the connection string, error text, or credentials in the response

#### 6. Write `middleware/logging.py`

Starlette middleware that:
- Generates a UUID `request_id` per request
- Attaches it to `request.state`
- After the response, emits one structured JSON log line:
  `{request_id, method, path, status_code, duration_ms, user_id}`
- **Never** logs passwords, file contents, API keys, or env vars

#### 7. Auth hardening

In `app.py` (or the new `routers/auth.py`):

- Password strength: minimum 8 chars, at least one digit (raise `WEAK_PASSWORD` error code)
- Login error message is always `"invalid credentials"` regardless of whether the username or password was wrong
- Cookie flags: `HttpOnly=True, Secure=True, SameSite="lax"`
- Session expiry: add `max_age=86400` (24 h) to `SessionMiddleware`
- Replace every `detail=str(e)` in `register`, `login`, `change_password` with the error envelope
- Migrate in-memory `conversation_store` in `chatbox.py` to a `chat_sessions` DB table with `(id, user_id, messages JSON, created_at)`

#### 8. Write `tests/test_auth.py`

| Test | Expected |
|------|----------|
| Register valid user | 200 |
| Register duplicate username | 400, error envelope |
| Login valid credentials | 200 |
| Login wrong password | 401, generic message |
| Protected route without session | 401 |
| Change password — wrong current password | 401 |
| Change password — weak new password | 400, `WEAK_PASSWORD` code |

#### 9. Write `tests/test_jobs.py`

| Test | Expected |
|------|----------|
| Job status immediately after POST | `status: "queued"` |
| Job status after mock run completes | `status: "completed"` |
| Job status with wrong user | 403 |
| Job failure path | `status: "failed"`, no raw exception text |
| Unknown job_id | 404 |

---

## Integration Point

Person 2's `job_service.run_job` calls Person 1's `AnalysisService.run`.
The signature above in Person 1's task 3 is the contract — do not change it
without telling both engineers.

Person 2 catches every exception in `run_job`, sets `status='failed'`, and
stores a sanitized error message (never the raw `str(e)` from internal errors).

Person 1 defines an `AnalysisError` hierarchy so Person 2 can distinguish
user-facing validation errors from internal system errors:

```python
class AnalysisError(Exception):
    """Base class for all analysis failures."""
    code: str = "ANALYSIS_ERROR"

class ValidationError(AnalysisError):
    code = "VALIDATION_ERROR"

class ParseError(AnalysisError):
    code = "PARSE_ERROR"
```

---

## CI/CD

Add `.github/workflows/ci.yml`:

```yaml
name: CI

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r backend/requirements.txt ruff
      - run: ruff check backend
      - run: pytest backend/tests -q

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm ci
        working-directory: frontend
      - run: npm run test -- --run
        working-directory: frontend
      - run: npm run build
        working-directory: frontend
```

Add `ruff` to `backend/requirements.txt` under a `# dev` comment.

---

## Recommended Build Order

```
Week 1 (both)    Agree on this plan → complete the Fix-Before-Features checklist →
                 define error envelope (Person 2 task 1)

Week 2 (split)   Person 1: AnalysisService + schemas
                 Person 2: require_auth middleware + JobService

Week 3 (split)   Person 1: analyses router + DB schema additions
                 Person 2: jobs router + health router + logging middleware

Week 4 (split)   Person 1: test_analyses.py
                 Person 2: test_auth.py + test_jobs.py + auth hardening

Week 5 (together) Integration point verification → frontend wiring →
                  CI/CD workflow → README + OpenAPI cleanup → end-to-end test pass
```
