from backend.config import Settings
from backend.database import get_db_connection


def test_get_db_connection_passes_configured_port(monkeypatch):
    captured = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("backend.database.mysql.connector.connect", fake_connect)

    settings = Settings(
        gemini_api_key=None,
        db_host="db.example.com",
        db_user="db-user",
        db_pass="db-pass",
        db_name="db-name",
        session_secret=None,
        db_port=23429,
    )

    get_db_connection(settings)

    assert captured["host"] == "db.example.com"
    assert captured["port"] == 23429
    assert captured["database"] == "db-name"
