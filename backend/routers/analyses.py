"""Authenticated analysis CRUD routes and process-local background wiring."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import ValidationError as PydanticValidationError

from ..database import get_db_connection
from ..middleware.auth import require_auth
from ..schemas.analysis import (
    AnalysisAcceptedResponse,
    AnalysisListPagination,
    AnalysisListResponse,
    AnalysisRequest,
    AnalysisResultResponse,
    AnalysisSummary,
    DeviationData,
    ZoneWeight,
)
from ..services import job_service
from ..services.analysis_service import AnalysisError, AnalysisService


router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "details": {}},
    )


def _close_connection(db, *, rollback: bool = False) -> None:
    if db is None:
        return
    if rollback:
        try:
            db.rollback()
        except Exception:
            pass
    try:
        db.close()
    except Exception:
        pass


def _json_value(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, (str, bytes, bytearray)):
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return default
    return value


def _analysis_response(row: dict[str, Any]) -> AnalysisResultResponse:
    sample_filenames = _json_value(row.get("sample_filenames"), []) or []
    scores = _json_value(row.get("scores"))
    deviation = _json_value(row.get("deviation_data"))
    summary = _json_value(row.get("summary"))

    if deviation is not None:
        deviation = DeviationData(
            x=deviation.get("x", []),
            deviation=deviation.get("deviation", []),
            max_deviation=deviation.get("max_deviation", deviation.get("maxDeviation", 0.0)),
            avg_deviation=deviation.get("avg_deviation", deviation.get("avgDeviation", 0.0)),
        )
    if summary is not None:
        summary = AnalysisSummary(
            total=summary.get("total", summary.get("totalSamples", 0)),
            good=summary.get("good", 0),
            warning=summary.get("warning", 0),
            critical=summary.get("critical", 0),
        )
    if scores is not None:
        scores = {str(name): float(score) for name, score in scores.items()}

    return AnalysisResultResponse(
        analysis_id=row["id"],
        user_id=int(row["user_id"]),
        status=row["status"],
        baseline_filename=row.get("baseline_filename") or "",
        sample_filenames=[str(name) for name in sample_filenames],
        scoring_method=row.get("scoring_method", "hybrid"),
        scores=scores,
        deviation_data=deviation,
        summary=summary,
        error=row.get("error_message"),
        created_at=row["created_at"],
        completed_at=row.get("completed_at"),
    )


def _fetch_analysis(db, analysis_id: str) -> dict[str, Any] | None:
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT a.id, a.user_id, a.status, a.baseline_filename, a.sample_filenames,
               a.scoring_method, a.scores, a.deviation_data, a.summary,
               a.error_message, a.created_at, a.updated_at, a.completed_at,
               j.id AS job_id, j.status AS job_status, j.error_message AS job_error,
               j.created_at AS job_created_at, j.updated_at AS job_updated_at
        FROM analyses AS a
        LEFT JOIN jobs AS j ON j.analysis_id = a.id
        WHERE a.id = %s
        """,
        (analysis_id,),
    )
    return cursor.fetchone()


def _run_analysis_background(
    job_id: str,
    analysis_id: str,
    baseline_bytes: bytes,
    baseline_name: str,
    samples: list[tuple[bytes, str]],
    scoring_method: str,
    zone_weights: list[dict] | None,
) -> None:
    """Run work with a connection owned exclusively by the worker."""
    db = None
    try:
        db = get_db_connection()
        job_service.run_job(
            job_id,
            AnalysisService(),
            db,
            baseline_bytes,
            baseline_name,
            samples,
            scoring_method,
            zone_weights,
        )
    finally:
        _close_connection(db)


@router.post("", response_model=AnalysisAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_analysis(
    background_tasks: BackgroundTasks,
    baseline: UploadFile = File(...),
    samples: list[UploadFile] = File(...),
    scoring_method: str = Form("hybrid"),
    zone_weights: str | None = Form(None),
    user_id: int = Depends(require_auth),
):
    db = None
    try:
        baseline_bytes = await baseline.read()
        sample_data = [(await sample.read(), sample.filename or "sample") for sample in samples]
        baseline_name = baseline.filename or "baseline"

        parsed_weights = _json_value(zone_weights)
        if zone_weights is not None and not isinstance(parsed_weights, list):
            raise _error(422, "VALIDATION_ERROR", "zone_weights must be a JSON array")
        validated_weights = None
        if parsed_weights is not None:
            validated_weights = [ZoneWeight.model_validate(weight).model_dump() for weight in parsed_weights]

        request = AnalysisRequest(
            baseline=baseline,
            samples=samples,
            scoring_method=scoring_method,
            zone_weights=validated_weights,
        )
        AnalysisService().validate_inputs(baseline_bytes, baseline_name, sample_data)
        analysis_id = str(uuid4())

        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO analyses
                (id, user_id, scoring_method, zone_weights, status,
                 baseline_filename, sample_filenames)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                analysis_id,
                int(user_id),
                request.scoring_method,
                json.dumps(validated_weights) if validated_weights is not None else None,
                "queued",
                baseline_name,
                json.dumps([name for _, name in sample_data]),
            ),
        )
        job_id = job_service.create_job(analysis_id, int(user_id), db)
        db.commit()
    except HTTPException:
        _close_connection(db, rollback=True)
        raise
    except AnalysisError as exc:
        _close_connection(db, rollback=True)
        raise _error(422, "VALIDATION_ERROR", str(exc))
    except (PydanticValidationError, json.JSONDecodeError, TypeError, ValueError):
        _close_connection(db, rollback=True)
        raise _error(422, "VALIDATION_ERROR", "Invalid analysis request")
    except Exception:
        _close_connection(db, rollback=True)
        raise _error(status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "Unable to create analysis")
    else:
        _close_connection(db)

    background_tasks.add_task(
        _run_analysis_background,
        job_id,
        analysis_id,
        baseline_bytes,
        baseline_name,
        sample_data,
        request.scoring_method,
        validated_weights,
    )
    return AnalysisAcceptedResponse(job_id=job_id, analysis_id=analysis_id, status="queued")


@router.get("", response_model=AnalysisListResponse)
def list_analyses(
    page: int = 1,
    limit: int = 20,
    user_id: int = Depends(require_auth),
):
    if page < 1 or limit < 1:
        raise _error(422, "VALIDATION_ERROR", "page and limit must be positive")

    db = None
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS total FROM analyses WHERE user_id = %s", (int(user_id),))
        count_row = cursor.fetchone() or {"total": 0}
        total = int(count_row.get("total", 0) if isinstance(count_row, dict) else count_row[0])
        cursor.execute(
            """
            SELECT id, user_id, status, baseline_filename, sample_filenames,
                   scoring_method, scores, deviation_data, summary,
                   error_message, created_at, updated_at, completed_at
            FROM analyses
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (int(user_id), limit, (page - 1) * limit),
        )
        rows = cursor.fetchall()
        return AnalysisListResponse(
            analyses=[_analysis_response(row) for row in rows],
            pagination=AnalysisListPagination(
                page=page,
                limit=limit,
                total=total,
                has_next=page * limit < total,
            ),
        )
    except HTTPException:
        raise
    except Exception:
        raise _error(status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "Unable to list analyses")
    finally:
        _close_connection(db, rollback=True)


@router.get("/{analysis_id}", response_model=AnalysisResultResponse)
def get_analysis(analysis_id: str, user_id: int = Depends(require_auth)):
    db = None
    try:
        db = get_db_connection()
        row = _fetch_analysis(db, analysis_id)
        if row is None:
            raise _error(404, "NOT_FOUND", "Analysis not found")
        if int(row["user_id"]) != int(user_id):
            raise _error(403, "FORBIDDEN", "Not allowed to access this analysis")
        return _analysis_response(row)
    except HTTPException:
        raise
    except Exception:
        raise _error(status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "Unable to retrieve analysis")
    finally:
        _close_connection(db, rollback=True)


@router.delete(
    "/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_202_ACCEPTED: {"model": AnalysisResultResponse}},
)
def delete_analysis(analysis_id: str, user_id: int = Depends(require_auth)):
    db = None
    try:
        db = get_db_connection()
        row = _fetch_analysis(db, analysis_id)
        if row is None:
            raise _error(404, "NOT_FOUND", "Analysis not found")
        if int(row["user_id"]) != int(user_id):
            raise _error(403, "FORBIDDEN", "Not allowed to delete this analysis")

        if row["status"] in ("queued", "processing"):
            cursor = db.cursor()
            cursor.execute(
                "UPDATE analyses SET status = 'cancelled' WHERE id = %s AND user_id = %s "
                "AND status IN ('queued', 'processing')",
                (analysis_id, int(user_id)),
            )
            cursor.execute(
                "UPDATE jobs SET status = 'cancelled' WHERE analysis_id = %s AND user_id = %s "
                "AND status IN ('queued', 'processing')",
                (analysis_id, int(user_id)),
            )
            db.commit()
            row["status"] = "cancelled"
            return Response(
                content=_analysis_response(row).model_dump_json(),
                status_code=status.HTTP_202_ACCEPTED,
                media_type="application/json",
            )

        cursor = db.cursor()
        cursor.execute("DELETE FROM jobs WHERE analysis_id = %s AND user_id = %s", (analysis_id, int(user_id)))
        cursor.execute("DELETE FROM analyses WHERE id = %s AND user_id = %s", (analysis_id, int(user_id)))
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        if db is not None:
            try:
                db.rollback()
            except Exception:
                pass
        raise
    except Exception:
        if db is not None:
            try:
                db.rollback()
            except Exception:
                pass
        raise _error(status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "Unable to delete analysis")
    finally:
        _close_connection(db)
