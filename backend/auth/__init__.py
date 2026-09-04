"""Authentication package: routes, session setup, and dependencies."""

from .dependencies import get_current_user_id, require_auth
from .router import router
from .session import configure_session_middleware

__all__ = [
    "configure_session_middleware",
    "get_current_user_id",
    "require_auth",
    "router",
]
