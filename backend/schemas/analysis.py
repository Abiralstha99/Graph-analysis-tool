"""Pydantic request and response models for FTIR analysis APIs."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict, Field, model_validator


ScoringMethod = Literal["hybrid", "rmse", "pearson", "area"]
AnalysisStatus = Literal["queued", "processing", "completed", "failed"]
SUPPORTED_SCORING_METHODS = frozenset(("hybrid", "rmse", "pearson", "area"))


class ZoneWeight(BaseModel):
    min: float
    max: float
    weight: float
    label: str
    key: str


class AnalysisRequest(BaseModel):
    """The multipart analysis request after FastAPI has parsed its fields."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline: UploadFile
    samples: list[UploadFile]
    scoring_method: str = "hybrid"
    zone_weights: list[ZoneWeight] | None = None

    @model_validator(mode="after")
    def validate_analysis_request(self) -> "AnalysisRequest":
        if not self.samples:
            raise ValueError("samples must not be empty")
        if self.scoring_method not in SUPPORTED_SCORING_METHODS:
            raise ValueError(f"unknown scoring method: {self.scoring_method}")
        return self


class AnalysisAcceptedResponse(BaseModel):
    job_id: UUID
    analysis_id: UUID
    status: Literal["queued"]


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: AnalysisStatus
    analysis_id: UUID | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class DeviationData(BaseModel):
    x: list[float]
    deviation: list[float]
    max_deviation: float
    avg_deviation: float


class AnalysisSummary(BaseModel):
    total: int = Field(ge=0)
    good: int = Field(ge=0)
    warning: int = Field(ge=0)
    critical: int = Field(ge=0)


class AnalysisResultResponse(BaseModel):
    analysis_id: UUID
    user_id: int
    status: AnalysisStatus
    baseline_filename: str
    sample_filenames: list[str]
    scoring_method: ScoringMethod
    scores: dict[str, float]
    deviation_data: DeviationData
    summary: AnalysisSummary
    created_at: datetime
    completed_at: datetime | None = None


class AnalysisListPagination(BaseModel):
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)
    has_next: bool


class AnalysisListResponse(BaseModel):
    analyses: list[AnalysisResultResponse]
    pagination: AnalysisListPagination


__all__ = [
    "AnalysisAcceptedResponse",
    "AnalysisListPagination",
    "AnalysisListResponse",
    "AnalysisRequest",
    "AnalysisResultResponse",
    "AnalysisStatus",
    "AnalysisSummary",
    "DeviationData",
    "JobStatusResponse",
    "ScoringMethod",
    "SUPPORTED_SCORING_METHODS",
    "ZoneWeight",
]
