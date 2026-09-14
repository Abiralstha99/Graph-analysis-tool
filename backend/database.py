"""Database connection helpers."""

import mysql.connector

from .config import Settings


def get_db_connection(settings: Settings | None = None):
    """Create a MySQL connection from configured database environment values.

    The caller owns the returned connection and must close it.
    """
    settings = settings or Settings.from_environment()
    if not all([settings.db_host, settings.db_user, settings.db_pass, settings.db_name]):
        raise RuntimeError("Database environment variables DB_HOST, DB_USER, DB_PASS, DB_NAME must be set")

    connect_kwargs = {
        "host": settings.db_host,
        "user": settings.db_user,
        "password": settings.db_pass,
        "database": settings.db_name,
        "autocommit": False,
    }
    if settings.db_port is not None:
        connect_kwargs["port"] = settings.db_port

    return mysql.connector.connect(**connect_kwargs)
