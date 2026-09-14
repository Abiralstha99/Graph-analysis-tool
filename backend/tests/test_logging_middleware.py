"""Access-log middleware: one JSON line per request, no secrets."""

import json
import logging
import os
import uuid

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from backend.middleware.logging import RequestLoggingMiddleware, configure_request_logging


LOGGER_NAME = "backend.middleware.logging"
LOG_FIELDS = {
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "user_id",
}


def build_app():
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SessionMiddleware, secret_key="test-secret")

    @app.get("/ping")
    def ping(request: Request):
        return {"request_id": str(request.state.request_id)}

    @app.post("/login")
    def login(request: Request, password: str = Form(...)):
        request.session["user_id"] = 7
        return {"ok": True}

    @app.get("/me")
    def me():
        return {"ok": True}

    @app.post("/upload")
    async def upload(file: UploadFile = File(...)):
        await file.read()
        return {"filename": file.filename}

    @app.get("/boom")
    def boom():
        raise RuntimeError("GEMINI_API_KEY=super-secret-key")

    return app


def latest_access_log(caplog):
    records = [record for record in caplog.records if record.name == LOGGER_NAME]
    assert records, "expected an access log record"
    payload = json.loads(records[-1].getMessage())
    assert set(payload) == LOG_FIELDS
    return payload


def test_stores_uuid_request_id_on_request_state(caplog):
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    client = TestClient(build_app())

    response = client.get("/ping")

    assert response.status_code == 200
    request_id = response.json()["request_id"]
    uuid.UUID(request_id)
    assert latest_access_log(caplog)["request_id"] == request_id


def test_emits_one_json_access_log_after_response(caplog):
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    client = TestClient(build_app())

    client.get("/ping")

    payload = latest_access_log(caplog)
    assert payload["method"] == "GET"
    assert payload["path"] == "/ping"
    assert payload["status_code"] == 200
    assert payload["user_id"] is None
    assert isinstance(payload["duration_ms"], (int, float))
    assert payload["duration_ms"] >= 0


def test_assigns_a_new_request_id_per_request(caplog):
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    client = TestClient(build_app())

    first = client.get("/ping").json()["request_id"]
    second = client.get("/ping").json()["request_id"]

    assert first != second
    records = [record for record in caplog.records if record.name == LOGGER_NAME]
    assert len(records) == 2
    ids = [json.loads(record.getMessage())["request_id"] for record in records]
    assert ids == [first, second]


def test_logs_authenticated_user_id_from_session(caplog):
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    client = TestClient(build_app())

    client.post("/login", data={"password": "hunter2-not-for-logs"})
    client.get("/me")

    payload = latest_access_log(caplog)
    assert payload["path"] == "/me"
    assert payload["user_id"] == 7


def test_never_logs_passwords_file_contents_api_keys_or_env_vars(caplog, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "env-secret-do-not-log")
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    client = TestClient(build_app())
    secret_csv = "wavenumber,absorbance\n4000,0.12\nsecret-spectrum-payload\n"

    client.post(
        "/upload?api_key=sk-live-not-for-logs",
        files={"file": ("sample.csv", secret_csv, "text/csv")},
    )
    client.post("/login", data={"password": "hunter2-not-for-logs"})

    logged = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name == LOGGER_NAME
    )
    assert "hunter2-not-for-logs" not in logged
    assert "secret-spectrum-payload" not in logged
    assert "sk-live-not-for-logs" not in logged
    assert "env-secret-do-not-log" not in logged
    assert os.environ["GEMINI_API_KEY"] not in logged
    assert "password" not in logged.lower()


def test_configure_request_logging_registers_middleware():
    app = FastAPI()
    configure_request_logging(app)
    assert any(item.cls is RequestLoggingMiddleware for item in app.user_middleware)


def test_logs_status_when_handler_raises(caplog):
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    client = TestClient(build_app(), raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    payload = latest_access_log(caplog)
    assert payload["status_code"] == 500
    assert payload["path"] == "/boom"
    assert "super-secret-key" not in caplog.text
