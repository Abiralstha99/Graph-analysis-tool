"""Canonical error response schemas used across all API endpoints."""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Details of an error response."""
    code: str
    message: str
    details: dict = {}


class ErrorResponse(BaseModel):
    """Standard error response envelope for all 4xx/5xx responses."""

    error: ErrorDetail
