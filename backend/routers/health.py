"""Liveness and readiness probes. Never leak credentials or error text."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..database import get_db_connection

router = APIRouter(tags=["health"])


@router.get("/health/live")
def liveness():
    return {"status": "ok"}


@router.get("/health/ready")
def readiness():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return {"status": "ok", "db": "ok"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "error"},
        )
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
