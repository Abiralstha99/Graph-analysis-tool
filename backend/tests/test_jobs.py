from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from backend.middleware.auth import require_auth
from backend.routers.jobs import router


JOB_ID = "11111111-1111-1111-1111-111111111111"
ANALYSIS_ID = "22222222-2222-2222-2222-222222222222"


class JobCursor:
    def __init__(self, row):
        self.row = row

    def execute(self, sql, params):
        self.job_id = params[0]

    def fetchone(self):
        if self.job_id != JOB_ID:
            return None
        return self.row


class JobDB:
    def __init__(self, user_id=7):
        self.row = {
            "id": JOB_ID,
            "analysis_id": ANALYSIS_ID,
            "user_id": user_id,
            "status": "processing",
            "error_message": None,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
        self.closed = False

    def cursor(self, dictionary=False):
        return JobCursor(self.row)

    def close(self):
        self.closed = True


def build_client(user_id, db):
    app = FastAPI()
    app.include_router(router)

    @app.exception_handler(HTTPException)
    async def canonical_http_error(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

    async def authenticated_user():
        return user_id

    app.dependency_overrides[require_auth] = authenticated_user
    return TestClient(app)


def test_get_job_returns_job_status_for_owner(monkeypatch):
    db = JobDB()
    monkeypatch.setattr("backend.routers.jobs.get_db_connection", lambda: db)
    client = build_client(7, db)

    response = client.get(f"/api/v1/jobs/{JOB_ID}")

    assert response.status_code == 200
    assert response.json() == {
        "job_id": JOB_ID,
        "analysis_id": ANALYSIS_ID,
        "status": "processing",
        "error": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    assert db.closed


def test_get_job_preserves_ownership_and_not_found_responses(monkeypatch):
    db = JobDB(user_id=7)
    monkeypatch.setattr("backend.routers.jobs.get_db_connection", lambda: db)

    forbidden = build_client(99, db).get(f"/api/v1/jobs/{JOB_ID}")
    missing = build_client(7, db).get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")

    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"
