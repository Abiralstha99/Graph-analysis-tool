import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from backend.chatbox import router
from backend.middleware.auth import require_auth
from backend.chatbox import router
from backend.middleware.auth import require_auth
from backend.services.chat_session_service import (
    count_sessions,
    delete_session,
    get_session,
    save_session,
)


class RecordingDB:
    def __init__(self, fetchone_result=None):
        self.statements = []
        self.fetchone_result = fetchone_result
        self.committed = False

    def cursor(self, dictionary=False):
        return self

    def execute(self, sql, params=None):
        self.statements.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self.fetchone_result

    def commit(self):
        self.committed = True


def test_save_session_inserts_chat_sessions_row():
    db = RecordingDB()
    messages = [{"role": "user", "content": "hi", "timestamp": "2026-01-01T00:00:00"}]

    save_session(db, "conv_1", 7, messages)

    sql, params = db.statements[0]
    assert "INSERT INTO chat_sessions" in sql
    assert "(id,user_id,messages" in sql.replace(" ", "")
    assert params[0] == "conv_1"
    assert params[1] == 7
    assert json.loads(params[2]) == messages
    assert db.committed


def test_get_session_returns_messages_for_owner():
    messages = [{"role": "assistant", "content": "hello"}]
    db = RecordingDB(fetchone_result={"messages": json.dumps(messages)})

    result = get_session(db, "conv_1", 7)

    sql, params = db.statements[0]
    assert "FROM chat_sessions" in sql
    assert "user_id" in sql
    assert params == ("conv_1", 7)
    assert result == messages


def test_get_session_returns_none_when_missing():
    db = RecordingDB(fetchone_result=None)

    assert get_session(db, "conv_missing", 7) is None


def test_delete_session_removes_owned_row():
    db = RecordingDB()

    delete_session(db, "conv_1", 7)

    sql, params = db.statements[0]
    assert "DELETE FROM chat_sessions" in sql
    assert params == ("conv_1", 7)
    assert db.committed


def test_count_sessions_queries_chat_sessions_table():
    db = RecordingDB(fetchone_result=(3,))

    assert count_sessions(db) == 3
    sql, _params = db.statements[0]
    assert "COUNT" in sql.upper()
    assert "chat_sessions" in sql


def build_chat_client(monkeypatch, user_id=7):
    chat_app = FastAPI()
    chat_app.include_router(router)

    @chat_app.exception_handler(HTTPException)
    async def canonical_http_error(request: Request, exc: HTTPException):
        detail = exc.detail
        if not isinstance(detail, dict):
            detail = {"code": "ERROR", "message": str(detail), "details": {}}
        return JSONResponse(status_code=exc.status_code, content={"error": detail})

    async def authenticated_user():
        return user_id

    chat_app.dependency_overrides[require_auth] = authenticated_user
    return TestClient(chat_app)


def test_get_conversation_reads_persisted_session(monkeypatch):
    monkeypatch.setattr(
        "backend.chatbox.get_session",
        lambda db, conversation_id, user_id: [{"role": "user", "content": "hi"}],
        raising=False,
    )
    monkeypatch.setattr("backend.chatbox.get_db_connection", lambda: MagicMock(), raising=False)
    client = build_chat_client(monkeypatch)

    response = client.get("/chat/conversation/conv_1")

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": "conv_1",
        "messages": [{"role": "user", "content": "hi"}],
        "status": "success",
    }


def test_get_conversation_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(
        "backend.chatbox.get_session",
        lambda db, conversation_id, user_id: None,
        raising=False,
    )
    monkeypatch.setattr("backend.chatbox.get_db_connection", lambda: MagicMock(), raising=False)
    client = build_chat_client(monkeypatch)

    response = client.get("/chat/conversation/conv_missing")

    assert response.status_code == 404


def test_clear_conversation_deletes_persisted_session(monkeypatch):
    deleted = {}

    def fake_delete(db, conversation_id, user_id):
        deleted["id"] = conversation_id
        deleted["user_id"] = user_id

    monkeypatch.setattr("backend.chatbox.delete_session", fake_delete, raising=False)
    monkeypatch.setattr("backend.chatbox.get_db_connection", lambda: MagicMock(), raising=False)
    client = build_chat_client(monkeypatch)

    response = client.delete("/chat/conversation/conv_1")

    assert response.status_code == 200
    assert deleted == {"id": "conv_1", "user_id": 7}


def test_send_message_persists_messages_to_chat_sessions(monkeypatch):
    saved = {}

    def fake_save(db, conversation_id, user_id, messages):
        saved["id"] = conversation_id
        saved["user_id"] = user_id
        saved["messages"] = messages

    monkeypatch.setattr("backend.chatbox.GENAI_AVAILABLE", True)
    monkeypatch.setattr(
        "backend.chatbox.Settings.from_environment",
        classmethod(lambda cls: SimpleNamespace(gemini_api_key="test-key")),
    )
    monkeypatch.setattr("backend.chatbox.genai", MagicMock())
    model = MagicMock()
    model.generate_content.return_value = SimpleNamespace(text="hello")
    monkeypatch.setattr("backend.chatbox._get_model", lambda: model)
    monkeypatch.setattr("backend.chatbox.generate_conversation_id", lambda: "conv_fixed")
    monkeypatch.setattr("backend.chatbox.save_session", fake_save, raising=False)
    monkeypatch.setattr("backend.chatbox.get_db_connection", lambda: MagicMock(), raising=False)
    client = build_chat_client(monkeypatch)

    response = client.post("/chat/send_message", json={"message": "hi"})

    assert response.status_code == 200
    assert saved["id"] == "conv_fixed"
    assert saved["user_id"] == 7
    assert saved["messages"][0]["role"] == "user"
    assert saved["messages"][0]["content"] == "hi"
    assert saved["messages"][1]["role"] == "assistant"
    assert saved["messages"][1]["content"] == "hello"


def test_chatbox_no_longer_uses_in_memory_conversation_sessions():
    import backend.chatbox as chatbox

    assert not hasattr(chatbox, "conversation_sessions")
