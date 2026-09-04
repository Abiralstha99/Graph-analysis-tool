from fastapi import HTTPException, Request, status


async def require_auth(request: Request) -> int:
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="UNAUTHORIZED:Not authenticated",
        )
    return int(user_id)