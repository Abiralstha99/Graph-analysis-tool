from datetime import datetime, timezone
from io import BytesIO
from uuid import UUID

import pytest
from fastapi import UploadFile
from pydantic import ValidationError

from backend.schemas import (
    AnalysisAcceptedResponse,
    AnalysisListPagination,
    AnalysisListResponse,
    AnalysisRequest,
    AnalysisResultResponse,
    AnalysisStatus,
    AnalysisSummary,
    DeviationData,
    JobStatusResponse,
    ZoneWeight,
)
from backend.schemas.analysis import (
    AnalysisAcceptedResponse as DirectAnalysisAcceptedResponse,
    AnalysisListResponse as DirectAnalysisListResponse,
    AnalysisRequest as DirectAnalysisRequest,
    AnalysisResultResponse as DirectAnalysisResultResponse,
    DeviationData as DirectDeviationData,
    JobStatusResponse as DirectJobStatusResponse,
    ZoneWeight as DirectZoneWeight,
)


def upload(filename: str) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(b"x,y\n1,2\n"))


def test_analysis_models_are_importable_from_package_and_module():
    assert AnalysisRequest is DirectAnalysisRequest
    assert AnalysisAcceptedResponse is DirectAnalysisAcceptedResponse
    assert AnalysisListResponse is DirectAnalysisListResponse
    assert AnalysisResultResponse is DirectAnalysisResultResponse
    assert DeviationData is DirectDeviationData
    assert JobStatusResponse is DirectJobStatusResponse
    assert ZoneWeight is DirectZoneWeight


def test_analysis_request_defaults_and_accepts_supported_scoring_methods():
    request = AnalysisRequest(baseline=upload("baseline.csv"), samples=[upload("sample.csv")])

    assert request.scoring_method == "hybrid"
    assert request.zone_weights is None

    for method in ("hybrid", "rmse", "pearson", "area"):
        assert AnalysisRequest(
            baseline=upload("baseline.csv"),
            samples=[upload("sample.csv")],
            scoring_method=method,
        ).scoring_method == method


def test_analysis_request_rejects_empty_samples():
    with pytest.raises(ValidationError, match="samples must not be empty"):
        AnalysisRequest(baseline=upload("baseline.csv"), samples=[])


def test_analysis_request_rejects_unknown_scoring_method():
    with pytest.raises(ValidationError, match="unknown scoring method"):
        AnalysisRequest(
            baseline=upload("baseline.csv"),
            samples=[upload("sample.csv")],
            scoring_method="cosine",
        )


def test_response_models_match_agreed_wire_shapes():
    created = AnalysisAcceptedResponse(
        job_id="11111111-1111-1111-1111-111111111111",
        analysis_id="22222222-2222-2222-2222-222222222222",
        status="queued",
    )
    assert created.model_dump() == {
        "job_id": UUID("11111111-1111-1111-1111-111111111111"),
        "analysis_id": UUID("22222222-2222-2222-2222-222222222222"),
        "status": "queued",
    }

    deviation = DeviationData(
        x=[4000, 3999],
        deviation=[0.02, 0.01],
        max_deviation=0.45,
        avg_deviation=0.12,
    )
    result = AnalysisResultResponse(
        analysis_id="22222222-2222-2222-2222-222222222222",
        user_id=1,
        status="completed",
        baseline_filename="baseline.csv",
        sample_filenames=["s1.csv", "s2.csv"],
        scoring_method="hybrid",
        scores={"s1.csv": 87.4, "s2.csv": 63.1},
        deviation_data=deviation,
        summary=AnalysisSummary(total=2, good=1, warning=0, critical=1),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        completed_at=datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc),
    )
    listed = AnalysisListResponse(
        analyses=[result],
        pagination=AnalysisListPagination(page=1, limit=20, total=1, has_next=False),
    )

    assert listed.pagination.has_next is False
    assert listed.analyses[0].deviation_data.max_deviation == 0.45


def test_incomplete_analysis_serializes_nullable_result_fields():
    result = AnalysisResultResponse(
        analysis_id="22222222-2222-2222-2222-222222222222",
        user_id=1,
        status="processing",
        baseline_filename="baseline.csv",
        sample_filenames=["sample.csv"],
        scoring_method="hybrid",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert result.model_dump() == {
        "analysis_id": UUID("22222222-2222-2222-2222-222222222222"),
        "user_id": 1,
        "status": "processing",
        "baseline_filename": "baseline.csv",
        "sample_filenames": ["sample.csv"],
        "scoring_method": "hybrid",
        "scores": None,
        "deviation_data": None,
        "summary": None,
        "error": None,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "completed_at": None,
    }


def test_job_status_accepts_nullable_analysis_and_error():
    job = JobStatusResponse(
        job_id="11111111-1111-1111-1111-111111111111",
        status="failed",
        analysis_id=None,
        error="analysis failed",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    assert job.analysis_id is None
    assert job.error == "analysis failed"
    assert set(AnalysisStatus.__args__) == {
        "queued",
        "processing",
        "completed",
        "failed",
        "cancelled",
    }


def test_job_status_accepts_cancelled_status():
    job = JobStatusResponse(
        job_id="11111111-1111-1111-1111-111111111111",
        status="cancelled",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    assert job.status == "cancelled"
