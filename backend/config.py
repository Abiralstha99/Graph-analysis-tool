"""Application configuration loaded at initialization or request time."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None
    db_host: str | None
    db_user: str | None
    db_pass: str | None
    db_name: str | None
    session_secret: str | None

    @classmethod
    def from_environment(cls) -> "Settings":
        """Load current environment-backed settings without caching secrets."""
        load_dotenv()
        return cls(
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            db_host=os.getenv("DB_HOST"),
            db_user=os.getenv("DB_USER"),
            db_pass=os.getenv("DB_PASS"),
            db_name=os.getenv("DB_NAME"),
            session_secret=os.getenv("SESSION_SECRET") or os.getenv("SECRET_KEY"),
        )
