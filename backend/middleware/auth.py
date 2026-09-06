"""FastAPI auth dependency: canonical require_auth used by all protected routes."""

from fastapi import HTTPException, Request, status


async def require_auth(request: Request) -> int:
    """Return the authenticated user_id from the session.

    Raises a 401 using the canonical error envelope dict so the global
    HTTPException handler in app.py can format it correctly:

        {"error": {"code": "UNAUTHORIZED", "message": "Not authenticated", "details": {}}}
    """
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Not authenticated",
                "details": {},
            },
        )
    return int(user_id)
