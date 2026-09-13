"""Authenticated job-status polling route."""

from fastapi import APIRouter, Depends, HTTPException, status

from ..database import get_db_connection
from ..middleware.auth import require_auth
from ..schemas.analysis import JobStatusResponse
from ..services import job_service


router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, user_id: int = Depends(require_auth)):
    db = None
    try:
        db = get_db_connection()
        return job_service.get_job(job_id, int(user_id), db)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "Unable to retrieve job status",
                "details": {},
            },
        )
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                pass
