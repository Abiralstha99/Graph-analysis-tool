"""Session middleware setup for cookie-based auth."""

import secrets

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from ..config import Settings


def configure_session_middleware(app: FastAPI) -> None:
    """Attach SessionMiddleware using SESSION_SECRET / SECRET_KEY or a generated key."""
    session_secret = Settings.from_environment().session_secret or secrets.token_urlsafe(32)
    app.add_middleware(SessionMiddleware, secret_key=session_secret)
