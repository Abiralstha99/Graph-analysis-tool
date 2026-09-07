import uuid

from fastapi import HTTPException, status

try:
    from .analysis_service import AnalysisError
except ImportError:
    class AnalysisError(Exception):
        code = "ANALYSIS_ERROR"


def create_job(analysis_id: str, user_id: int, db) -> str:
    job_id = str(uuid.uuid4())
    cur = db.cursor()
    cur.execute(
        "INSERT INTO jobs (id, analysis_id, user_id, status, attempt) "
        "VALUES (%s, %s, %s, %s, %s)",
        (job_id, analysis_id, user_id, "queued", 0),
    )
    db.commit()
    return job_id

def _fetch_job(db, job_id: str):
    cur = db.cursor(dictionary=True)
    cur.execute(
        """
        SELECT id, analysis_id, user_id, status, error_message, created_at, updated_at
        FROM jobs
        WHERE id = %s
        """,
        (job_id,),
    )
    return cur.fetchone()

def get_job(job_id: str, user_id: int, db) -> dict:
    row = _fetch_job(db, job_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": "Job not found",
                "details": {},
            },
        )

    if int(row["user_id"]) != int(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Not allowed to access this job",
                "details": {},
            },
        )

    return {
        "job_id": row["id"],
        "status": row["status"],
        "analysis_id": row["analysis_id"],
        "error": row["error_message"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _sanitize_error(exc: BaseException) -> str:
    if isinstance(exc, AnalysisError):
        return str(exc)
    return "Analysis failed"


def _set_job_status(
    db,
    job_id: str,
    status_value: str,
    error_message: str | None = None,
    attempt: int | None = None,
) -> None:
    cur = db.cursor()
    if attempt is None:
        cur.execute(
            "UPDATE jobs SET status = %s, error_message = %s WHERE id = %s",
            (status_value, error_message, job_id),
        )
    else:
        cur.execute(
            "UPDATE jobs SET status = %s, error_message = %s, attempt = %s WHERE id = %s",
            (status_value, error_message, attempt, job_id),
        )
    db.commit()


def _set_analysis_status(
    db,
    analysis_id: str,
    status_value: str,
    error_message: str | None = None,
) -> None:
    cur = db.cursor()
    if status_value in ("completed", "failed"):
        cur.execute(
            "UPDATE analyses SET status = %s, error_message = %s, "
            "completed_at = CURRENT_TIMESTAMP WHERE id = %s",
            (status_value, error_message, analysis_id),
        )
    else:
        cur.execute(
            "UPDATE analyses SET status = %s, error_message = %s WHERE id = %s",
            (status_value, error_message, analysis_id),
        )
    db.commit()


def run_job(
    job_id: str,
    analysis_service,
    db,
    baseline_bytes: bytes,
    baseline_name: str,
    samples: list[tuple[bytes, str]],
    scoring_method: str = "hybrid",
    zone_weights: list[dict] | None = None,
) -> None:
    row = _fetch_job(db, job_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": "Job not found",
                "details": {},
            },
        )

    analysis_id = row["analysis_id"]
    _set_job_status(db, job_id, "processing", attempt=1)
    _set_analysis_status(db, analysis_id, "processing")

    try:
        analysis_service.run(
            baseline_bytes,
            baseline_name,
            samples,
            scoring_method,
            zone_weights,
            analysis_id,
            db,
        )
    except Exception as exc:
        message = _sanitize_error(exc)
        _set_job_status(db, job_id, "failed", error_message=message)
        _set_analysis_status(db, analysis_id, "failed", error_message=message)
        return

    _set_job_status(db, job_id, "completed", error_message=None)
    _set_analysis_status(db, analysis_id, "completed")
 