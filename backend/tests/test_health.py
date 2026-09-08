"""Route tests for liveness and readiness probes."""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers.health import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_live_returns_ok_without_database():
    with patch("backend.routers.health.get_db_connection") as get_db:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    get_db.assert_not_called()


def test_ready_returns_ok_when_database_responds():
    conn = MagicMock()
    conn.cursor.return_value.fetchone.return_value = (1,)

    with patch("backend.routers.health.get_db_connection", return_value=conn):
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}
    conn.cursor.return_value.execute.assert_called_once_with("SELECT 1")
    conn.close.assert_called_once()


def test_ready_returns_degraded_when_database_fails():
    with patch(
        "backend.routers.health.get_db_connection",
        side_effect=RuntimeError("Failed to connect using mysql://user:hunter2@db-host/secret_db"),
    ):
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "db": "error"}
    assert "hunter2" not in response.text
    assert "db-host" not in response.text
    assert "secret_db" not in response.text


def test_ready_closes_connection_when_query_fails():
    conn = MagicMock()
    conn.cursor.return_value.execute.side_effect = RuntimeError(
        "Lost connection to mysql://user:hunter2@db-host/secret_db"
    )

    with patch("backend.routers.health.get_db_connection", return_value=conn):
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "db": "error"}
    assert "hunter2" not in response.text
    conn.close.assert_called_once()
