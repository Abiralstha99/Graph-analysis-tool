import json
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.middleware.auth import require_auth
from backend.routers.analyses import router


app = FastAPI()
app.include_router(router)


@app.exception_handler(HTTPException)
async def canonical_http_error(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {
        "code": "INTERNAL_ERROR",
        "message": str(exc.detail),
        "details": {},
    }
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.exception_handler(RequestValidationError)
async def canonical_request_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": "Invalid request", "details": {}}},
    )


async def authenticated_user():
    return 7


app.dependency_overrides[require_auth] = authenticated_user
client = TestClient(app)


def csv_file(name, body="metadata\nx,y\n1,2\n2,3\n"):
    return (name, body, "text/csv")


def test_create_analysis_queues_background_work_with_serialized_uploads(monkeypatch):
    connection = MagicMock()
    monkeypatch.setattr("backend.routers.analyses.get_db_connection", lambda: connection)
    monkeypatch.setattr(
        "backend.routers.analyses.job_service.create_job",
        lambda analysis_id, user_id, db: "11111111-1111-1111-1111-111111111111",
    )
    background_calls = []

    def capture_background(*args):
        background_calls.append(args)

    monkeypatch.setattr("backend.routers.analyses._run_analysis_background", capture_background)

    response = client.post(
        "/api/v1/analyses",
        data={
            "scoring_method": "rmse",
            "zone_weights": json.dumps(
                [{"min": 1, "max": 3, "weight": 50, "label": "all", "key": "all"}]
            ),
        },
        files=[
            ("baseline", csv_file("baseline.csv", "metadata\nx,y\n1,2\n2,3\n")),
            ("samples", csv_file("sample.csv", "metadata\nx,y\n1,4\n2,5\n")),
        ],
    )

    assert response.status_code == 202
    body = response.json()
    assert body["job_id"] == "11111111-1111-1111-1111-111111111111"
    assert body["analysis_id"]
    assert body["status"] == "queued"
    assert connection.commit.called
    assert connection.close.called
    assert len(background_calls) == 1
    assert background_calls[0][2:6] == (
        b"metadata\nx,y\n1,2\n2,3\n",
        "baseline.csv",
        [(b"metadata\nx,y\n1,4\n2,5\n", "sample.csv")],
        "rmse",
    )
    assert background_calls[0][6] == [
        {"min": 1.0, "max": 3.0, "weight": 50.0, "label": "all", "key": "all"}
    ]


def test_create_analysis_rejects_empty_samples_with_canonical_error():
    response = client.post(
        "/api/v1/analyses",
        files=[("baseline", csv_file("baseline.csv"))],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    ("filename", "contents"),
    [
        ("baseline.pdf", "metadata\nx,y\n1,2\n2,3\n"),
        ("baseline.csv", "metadata\nx,y\n1,2\n"),
        ("baseline.csv", "metadata\nx,y\n1,nope\n2,3\n"),
    ],
)
def test_create_analysis_rejects_invalid_upload_before_persisting(monkeypatch, filename, contents):
    def fail_if_db_requested():
        raise AssertionError("invalid uploads must not create a database connection")

    monkeypatch.setattr("backend.routers.analyses.get_db_connection", fail_if_db_requested)

    response = client.post(
        "/api/v1/analyses",
        files=[
            ("baseline", csv_file(filename, contents)),
            ("samples", csv_file("sample.csv")),
        ],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_analysis_rejects_oversized_upload_before_persisting(monkeypatch):
    def fail_if_db_requested():
        raise AssertionError("oversized uploads must not create a database connection")

    monkeypatch.setattr("backend.routers.analyses.get_db_connection", fail_if_db_requested)

    response = client.post(
        "/api/v1/analyses",
        files=[
            ("baseline", csv_file("baseline.csv", "x" * (10 * 1024 * 1024 + 1))),
            ("samples", csv_file("sample.csv")),
        ],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_background_worker_opens_and_closes_its_own_connection(monkeypatch):
    worker_connection = MagicMock()
    calls = []
    monkeypatch.setattr("backend.routers.analyses.get_db_connection", lambda: worker_connection)
    monkeypatch.setattr(
        "backend.routers.analyses.job_service.run_job",
        lambda *args: calls.append(args),
    )

    from backend.routers.analyses import _run_analysis_background

    _run_analysis_background(
        "job-id",
        "analysis-id",
        b"baseline",
        "baseline.csv",
        [(b"sample", "sample.csv")],
        "hybrid",
        None,
    )

    assert calls[0][0] == "job-id"
    assert calls[0][2] is worker_connection
    assert worker_connection.close.called


def analysis_row(analysis_id=None, user_id=7, status="completed"):
    analysis_id = analysis_id or str(uuid4())
    return {
        "id": analysis_id,
        "user_id": user_id,
        "status": status,
        "baseline_filename": "baseline.csv",
        "sample_filenames": ["sample.csv"],
        "scoring_method": "hybrid",
        "scores": {"sample.csv": 100.0} if status == "completed" else None,
        "deviation_data": {
            "x": [1.0],
            "deviation": [0.0],
            "maxDeviation": 0.0,
            "avgDeviation": 0.0,
        } if status == "completed" else None,
        "summary": {"totalSamples": 1, "good": 1, "warning": 0, "critical": 0}
        if status == "completed" else None,
        "error_message": None,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "completed_at": datetime(2026, 1, 1, tzinfo=timezone.utc)
        if status == "completed" else None,
        "job_id": str(uuid4()),
        "job_status": status,
        "job_error": None,
        "job_created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "job_updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }


class AnalysisCursor:
    def __init__(self, db):
        self.db = db
        self.result = None

    def execute(self, sql, params=()):
        if "COUNT(*)" in sql:
            user_id = params[0]
            self.result = [{"total": sum(row["user_id"] == user_id for row in self.db.rows.values())}]
        elif "FROM analyses AS a" in sql:
            self.result = self.db.rows.get(params[0])
        elif "FROM analyses" in sql and "SELECT id" in sql:
            user_id = params[0]
            rows = [row for row in self.db.rows.values() if row["user_id"] == user_id]
            self.result = rows[params[2]:params[2] + params[1]]
        elif "INSERT INTO analyses" in sql:
            self.db.rows[params[0]] = analysis_row(params[0], params[1], params[4])
            self.db.rows[params[0]]["scoring_method"] = params[2]
        elif "UPDATE analyses SET status = 'cancelled'" in sql:
            self.db.rows[params[0]]["status"] = "cancelled"
        elif "UPDATE jobs SET status = 'cancelled'" in sql:
            pass
        elif "DELETE FROM jobs" in sql:
            pass
        elif "DELETE FROM analyses" in sql:
            self.db.rows.pop(params[0], None)
        else:
            raise AssertionError(f"Unhandled SQL: {sql}")

    def fetchone(self):
        return self.result[0] if isinstance(self.result, list) else self.result

    def fetchall(self):
        return self.result


class AnalysisDB:
    def __init__(self, rows):
        self.rows = {row["id"]: row for row in rows}
        self.closed = False

    def cursor(self, dictionary=False):
        return AnalysisCursor(self)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.closed = True


def test_list_analysis_is_scoped_to_authenticated_user(monkeypatch):
    own = analysis_row(user_id=7)
    other = analysis_row(user_id=99)
    db = AnalysisDB([own, other])
    monkeypatch.setattr("backend.routers.analyses.get_db_connection", lambda: db)

    response = client.get("/api/v1/analyses")

    assert response.status_code == 200
    assert [item["user_id"] for item in response.json()["analyses"]] == [7]
    assert db.closed


def test_detail_always_returns_analysis_shape(monkeypatch):
    completed = analysis_row(status="completed")
    processing = analysis_row(status="processing")
    db = AnalysisDB([completed, processing])
    monkeypatch.setattr("backend.routers.analyses.get_db_connection", lambda: db)

    completed_response = client.get(f"/api/v1/analyses/{completed['id']}")
    processing_response = client.get(f"/api/v1/analyses/{processing['id']}")

    assert completed_response.status_code == 200
    assert completed_response.json()["scores"] == {"sample.csv": 100.0}
    assert processing_response.status_code == 200
    assert processing_response.json()["status"] == "processing"
    assert processing_response.json()["baseline_filename"] == "baseline.csv"
    assert processing_response.json()["sample_filenames"] == ["sample.csv"]
    assert processing_response.json()["scores"] is None
    assert "job_id" not in processing_response.json()


def test_active_delete_cancels_and_retains_analysis(monkeypatch):
    row = analysis_row(status="processing")
    db = AnalysisDB([row])
    monkeypatch.setattr("backend.routers.analyses.get_db_connection", lambda: db)

    response = client.delete(f"/api/v1/analyses/{row['id']}")

    assert response.status_code == 202
    assert response.json()["status"] == "cancelled"
    assert response.json()["analysis_id"] == row["id"]
    assert response.json()["baseline_filename"] == "baseline.csv"
    assert "job_id" not in response.json()
    assert row["id"] in db.rows
    assert db.rows[row["id"]]["status"] == "cancelled"


def test_terminal_delete_removes_analysis(monkeypatch):
    row = analysis_row(status="failed")
    db = AnalysisDB([row])
    monkeypatch.setattr("backend.routers.analyses.get_db_connection", lambda: db)

    response = client.delete(f"/api/v1/analyses/{row['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert row["id"] not in db.rows


@pytest.mark.parametrize("status", ["completed", "failed", "cancelled"])
def test_terminal_statuses_are_physically_deleted(monkeypatch, status):
    row = analysis_row(status=status)
    db = AnalysisDB([row])
    monkeypatch.setattr("backend.routers.analyses.get_db_connection", lambda: db)

    response = client.delete(f"/api/v1/analyses/{row['id']}")

    assert response.status_code == 204
    assert row["id"] not in db.rows


def test_detail_rejects_other_owner(monkeypatch):
    row = analysis_row(user_id=99)
    db = AnalysisDB([row])
    monkeypatch.setattr("backend.routers.analyses.get_db_connection", lambda: db)

    response = client.get(f"/api/v1/analyses/{row['id']}")

    assert response.status_code == 403
    assert response.json()["error"] == {
        "code": "FORBIDDEN",
        "message": "Not allowed to access this analysis",
        "details": {},
    }


def test_detail_returns_not_found_for_unknown_analysis(monkeypatch):
    db = AnalysisDB([])
    monkeypatch.setattr("backend.routers.analyses.get_db_connection", lambda: db)

    response = client.get(f"/api/v1/analyses/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
