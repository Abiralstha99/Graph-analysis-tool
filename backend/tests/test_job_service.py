"""Tests for services/job_service.py, backed by an in-memory fake DB."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from backend.services.job_service import (
    AnalysisError,
    _set_analysis_status,
    _set_job_status,
    create_job,
    get_job,
    run_job,
)

ANALYSIS_ID = "22222222-2222-2222-2222-222222222222"
UNKNOWN_JOB_ID = "00000000-0000-0000-0000-000000000000"


class FakeCursor:
    def __init__(self, db):
        self._db = db
        self._result = None

    def execute(self, sql, params=()):
        if "INSERT INTO jobs" in sql:
            job_id, analysis_id, user_id, status, attempt = params
            self._db.jobs[job_id] = {
                "id": job_id,
                "analysis_id": analysis_id,
                "user_id": user_id,
                "status": status,
                "attempt": attempt,
                "error_message": None,
                "created_at": None,
                "updated_at": None,
            }
            return

        if "UPDATE jobs" in sql or "UPDATE analyses" in sql:
            store = self._db.jobs if "UPDATE jobs" in sql else self._db.analyses
            columns = _set_columns(sql)
            *values, row_id = params
            row = store.get(row_id)
            if row is not None:
                row.update(dict(zip(columns, values)))
                if "CURRENT_TIMESTAMP" in sql:
                    row["completed_at"] = "CURRENT_TIMESTAMP"
            return

        if "SELECT" in sql and "FROM jobs" in sql:
            (job_id,) = params
            self._result = self._db.jobs.get(job_id)
            return

        raise NotImplementedError(f"FakeCursor cannot handle SQL: {sql}")

    def fetchone(self):
        return self._result


def _set_columns(sql):
    # e.g. "UPDATE jobs SET status = %s, attempt = %s WHERE id = %s"
    # -> ["status", "attempt"]. Assumes the last bound param is the WHERE id.
    set_clause = sql.split("SET", 1)[1]
    if "WHERE" in set_clause:
        set_clause = set_clause.split("WHERE", 1)[0]
    return [
        assignment.split("=")[0].strip()
        for assignment in set_clause.split(",")
        if "%s" in assignment
    ]


class FakeDB:
    """Minimal stand-in for a mysql.connector connection, keyed by row id."""

    def __init__(self):
        self.jobs = {}
        self.analyses = {
            ANALYSIS_ID: {
                "id": ANALYSIS_ID,
                "user_id": 1,
                "status": "queued",
                "error_message": None,
                "completed_at": None,
            }
        }

    def cursor(self, dictionary=False):
        return FakeCursor(self)

    def commit(self):
        pass

    def close(self):
        pass


class FakeAnalysisService:
    def run(self, *args, **kwargs):
        self.called_with = args
        return None


class FailingAnalysisService:
    def __init__(self, error):
        self._error = error

    def run(self, *args, **kwargs):
        raise self._error


class FlakyService:
    def __init__(self):
        self.n = 0

    def run(self, *args, **kwargs):
        self.n += 1
        if self.n < 3:
            raise RuntimeError("transient")
        return None


class CancellingService:
    def __init__(self, db, job_id):
        self.db = db
        self.job_id = job_id
        self.calls = 0

    def run(self, *args, **kwargs):
        self.calls += 1
        self.db.jobs[self.job_id]["status"] = "cancelled"
        self.db.analyses[ANALYSIS_ID]["status"] = "cancelled"


def test_create_job_inserts_queued_row():
    db = FakeDB()

    job_id = create_job(ANALYSIS_ID, 1, db)

    assert isinstance(job_id, str)
    assert len(job_id) == 36
    assert db.jobs[job_id]["status"] == "queued"
    assert db.jobs[job_id]["user_id"] == 1
    assert db.jobs[job_id]["analysis_id"] == ANALYSIS_ID
    assert db.jobs[job_id]["attempt"] == 0


def test_get_job_returns_queued_status_for_owner():
    db = FakeDB()
    job_id = create_job(ANALYSIS_ID, 1, db)

    job = get_job(job_id, 1, db)

    assert job["status"] == "queued"
    assert job["error"] is None


def test_get_job_raises_forbidden_for_wrong_user():
    db = FakeDB()
    job_id = create_job(ANALYSIS_ID, 1, db)

    with pytest.raises(HTTPException) as raised:
        get_job(job_id, 99, db)

    assert raised.value.status_code == 403
    assert raised.value.detail == {
        "code": "FORBIDDEN",
        "message": "Not allowed to access this job",
        "details": {},
    }


def test_get_job_raises_not_found_for_unknown_id():
    db = FakeDB()

    with pytest.raises(HTTPException) as raised:
        get_job(UNKNOWN_JOB_ID, 1, db)

    assert raised.value.status_code == 404
    assert raised.value.detail == {
        "code": "NOT_FOUND",
        "message": "Job not found",
        "details": {},
    }


def test_set_job_status_updates_queued_row():
    db = FakeDB()
    job_id = create_job(ANALYSIS_ID, 1, db)

    _set_job_status(db, job_id, "processing", attempt=1)

    assert db.jobs[job_id]["status"] == "processing"
    assert db.jobs[job_id]["attempt"] == 1


def test_set_analysis_status_sets_completed_at_when_completed():
    db = FakeDB()

    _set_analysis_status(db, ANALYSIS_ID, "processing")
    assert db.analyses[ANALYSIS_ID]["status"] == "processing"
    assert db.analyses[ANALYSIS_ID]["completed_at"] is None

    _set_analysis_status(db, ANALYSIS_ID, "completed")
    assert db.analyses[ANALYSIS_ID]["status"] == "completed"
    assert db.analyses[ANALYSIS_ID]["completed_at"] is not None


def test_run_job_marks_job_and_analysis_completed():
    db = FakeDB()
    job_id = create_job(ANALYSIS_ID, 1, db)
    analysis_service = FakeAnalysisService()

    run_job(job_id, analysis_service, db, b"a", "b.csv", [(b"s", "s.csv")])

    job = get_job(job_id, 1, db)
    assert job["status"] == "completed"
    assert job["error"] is None
    assert db.analyses[ANALYSIS_ID]["status"] == "completed"
    assert analysis_service.called_with[5] == ANALYSIS_ID
    assert analysis_service.called_with[6] is db


def test_run_job_marks_job_failed_on_analysis_error():
    db = FakeDB()
    job_id = create_job(ANALYSIS_ID, 1, db)
    analysis_service = FailingAnalysisService(
        AnalysisError("CSV must have two numeric columns")
    )

    with patch("backend.services.job_service.time.sleep") as slept:
        run_job(job_id, analysis_service, db, b"a", "b.csv", [(b"s", "s.csv")])

    job = get_job(job_id, 1, db)
    assert job["status"] == "failed"
    assert job["error"] == "CSV must have two numeric columns"
    assert db.analyses[ANALYSIS_ID]["status"] == "failed"
    assert db.analyses[ANALYSIS_ID]["error_message"] == (
        "CSV must have two numeric columns"
    )
    assert slept.call_count == 0


def test_run_job_marks_job_failed_without_internal_error_text():
    db = FakeDB()
    job_id = create_job(ANALYSIS_ID, 1, db)
    secret = "password=hunter2 connection=mysql://"
    analysis_service = FailingAnalysisService(RuntimeError(secret))

    with patch("backend.services.job_service.time.sleep") as slept:
        run_job(job_id, analysis_service, db, b"a", "b.csv", [(b"s", "s.csv")])

    job = get_job(job_id, 1, db)
    assert job["status"] == "failed"
    assert job["error"] == "Analysis failed"
    assert secret not in str(job)
    assert db.jobs[job_id]["error_message"] == "Analysis failed"
    assert db.analyses[ANALYSIS_ID]["status"] == "failed"
    assert db.analyses[ANALYSIS_ID]["error_message"] == "Analysis failed"
    assert secret not in str(db.jobs[job_id])
    assert secret not in str(db.analyses[ANALYSIS_ID])
    assert slept.call_count == 2


def test_run_job_retries_transient_errors_then_completes():
    db = FakeDB()
    job_id = create_job(ANALYSIS_ID, 1, db)
    analysis_service = FlakyService()

    with patch("backend.services.job_service.time.sleep") as slept:
        run_job(job_id, analysis_service, db, b"a", "b.csv", [(b"s", "s.csv")])

    job = get_job(job_id, 1, db)
    assert job["status"] == "completed"
    assert job["error"] is None
    assert slept.call_count == 2
    assert analysis_service.n == 3


def test_run_job_fails_after_three_generic_errors():
    db = FakeDB()
    job_id = create_job(ANALYSIS_ID, 1, db)
    analysis_service = FailingAnalysisService(RuntimeError("transient"))

    with patch("backend.services.job_service.time.sleep") as slept:
        run_job(job_id, analysis_service, db, b"a", "b.csv", [(b"s", "s.csv")])

    job = get_job(job_id, 1, db)
    assert job["status"] == "failed"
    assert job["error"] == "Analysis failed"
    assert "transient" not in str(job)
    assert slept.call_count == 2
    assert db.jobs[job_id]["attempt"] == 3


def test_run_job_skips_cancelled_job_without_calling_analysis_service():
    db = FakeDB()
    job_id = create_job(ANALYSIS_ID, 1, db)
    db.jobs[job_id]["status"] = "cancelled"
    service = FakeAnalysisService()

    run_job(job_id, service, db, b"a", "b.csv", [(b"s", "s.csv")])

    assert not hasattr(service, "called_with")
    assert db.jobs[job_id]["status"] == "cancelled"


def test_run_job_does_not_overwrite_cancellation_during_analysis():
    db = FakeDB()
    job_id = create_job(ANALYSIS_ID, 1, db)
    service = CancellingService(db, job_id)

    run_job(job_id, service, db, b"a", "b.csv", [(b"s", "s.csv")])

    assert service.calls == 1
    assert db.jobs[job_id]["status"] == "cancelled"
    assert db.analyses[ANALYSIS_ID]["status"] == "cancelled"
