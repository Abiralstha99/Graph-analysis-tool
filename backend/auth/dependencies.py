"""FastAPI auth dependencies."""

from fastapi import HTTPException, Request, status


async def get_current_user_id(request: Request) -> int:
    """Return the authenticated user id from the session, or raise 401."""
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return int(user_id)


# Alias used by the infrastructure plan / future callers.
require_auth = get_current_user_id
