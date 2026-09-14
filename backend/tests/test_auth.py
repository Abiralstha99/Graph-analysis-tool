import importlib

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from mysql.connector import IntegrityError
from starlette.middleware.sessions import SessionMiddleware

auth_routes = importlib.import_module("backend.auth.router")
from backend.auth.router import change_password, register, router as auth_router
from backend.auth.session import configure_session_middleware
from backend.middleware.auth import require_auth
from backend.schemas.auth import ChangePasswordPayload, UserAuth
from backend.services.auth_service import validate_password_strength


STRONG_PASSWORD = "password1"
WEAK_SHORT_PASSWORD = "abc123"
WEAK_NO_DIGIT_PASSWORD = "abcdefgh"


@pytest.fixture
def anyio_backend():
    """Exercise the application's supported asyncio runtime only."""
    return "asyncio"


def make_request(session: dict) -> Request:
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/protected",
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "scheme": "http",
        "client": ("testclient", 50000),
        "root_path": "",
    })
    request.scope["session"] = session
    return request


@pytest.mark.anyio
async def test_require_auth_returns_session_user_id():
    assert await require_auth(make_request({"user_id": "42"})) == 42


@pytest.mark.anyio
async def test_require_auth_raises_canonical_unauthorized_error():
    with pytest.raises(HTTPException) as raised:
        await require_auth(make_request({}))

    assert raised.value.status_code == 401
    assert raised.value.detail == {
        "code": "UNAUTHORIZED",
        "message": "Not authenticated",
        "details": {},
    }


def test_password_strength_rejects_fewer_than_eight_characters():
    with pytest.raises(HTTPException) as raised:
        validate_password_strength(WEAK_SHORT_PASSWORD)

    assert raised.value.status_code == 400
    assert raised.value.detail["code"] == "WEAK_PASSWORD"
    assert raised.value.detail["details"] == {}


def test_password_strength_rejects_password_without_a_digit():
    with pytest.raises(HTTPException) as raised:
        validate_password_strength(WEAK_NO_DIGIT_PASSWORD)

    assert raised.value.status_code == 400
    assert raised.value.detail["code"] == "WEAK_PASSWORD"


def test_password_strength_accepts_eight_characters_with_a_digit():
    validate_password_strength(STRONG_PASSWORD)


def test_session_middleware_sets_cookie_flags_and_max_age():
    session_app = FastAPI()
    configure_session_middleware(session_app)
    middleware = next(
        item for item in session_app.user_middleware if item.cls is SessionMiddleware
    )

    assert middleware.kwargs["https_only"] is True
    assert middleware.kwargs["same_site"] == "lax"
    assert middleware.kwargs["max_age"] == 86400


class UserStore:
    def __init__(self):
        self.users_by_username = {}
        self.users_by_id = {}
        self.next_id = 1


class UserCursor:
    def __init__(self, store: UserStore):
        self.store = store
        self._row = None

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split()).lower()
        if normalized.startswith("insert into users"):
            username, password = params
            if username in self.store.users_by_username:
                raise IntegrityError("duplicate username")
            user_id = self.store.next_id
            self.store.next_id += 1
            row = {"id": user_id, "username": username, "password": password}
            self.store.users_by_username[username] = row
            self.store.users_by_id[user_id] = row
            return
        if "from users where username" in normalized:
            self._row = self.store.users_by_username.get(params[0])
            return
        if "from users where id" in normalized:
            self._row = self.store.users_by_id.get(int(params[0]))
            return
        if normalized.startswith("update users set password"):
            password, user_id = params
            row = self.store.users_by_id[int(user_id)]
            row["password"] = password
            return
        raise AssertionError(f"unexpected SQL: {sql}")

    def fetchone(self):
        return self._row


class UserDB:
    def __init__(self, store: UserStore):
        self.store = store

    def cursor(self, dictionary=False):
        return UserCursor(self.store)

    def commit(self):
        return None

    def close(self):
        return None


def _error_envelope(response):
    body = response.json()
    assert "error" in body
    assert set(body["error"]) >= {"code", "message", "details"}
    return body["error"]


def build_auth_client(monkeypatch, store=None):
    store = store or UserStore()
    monkeypatch.setattr(auth_routes, "get_db_connection", lambda: UserDB(store))
    isolated = FastAPI()

    @isolated.exception_handler(HTTPException)
    async def canonical_http_error(request: Request, exc: HTTPException):
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "code": detail["code"],
                        "message": detail["message"],
                        "details": detail.get("details", {}),
                    }
                },
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "UNWRAPPED", "message": str(detail), "details": {}}},
        )

    isolated.include_router(auth_router)
    configure_session_middleware(isolated)

    @isolated.get("/protected")
    async def protected(user_id: int = Depends(require_auth)):
        return {"user_id": user_id}

    return TestClient(isolated, base_url="https://testserver"), store


def test_register_valid_user(monkeypatch):
    client, store = build_auth_client(monkeypatch)

    response = client.post(
        "/register",
        json={"username": "alice", "password": STRONG_PASSWORD},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "username": "alice"}
    assert "alice" in store.users_by_username


def test_register_duplicate_username_returns_error_envelope(monkeypatch):
    client, _store = build_auth_client(monkeypatch)
    payload = {"username": "alice", "password": STRONG_PASSWORD}
    client.post("/register", json=payload)

    response = client.post("/register", json=payload)

    assert response.status_code == 400
    error = _error_envelope(response)
    assert error["code"] == "VALIDATION_ERROR"
    assert error["message"] == "username already exists"
    assert error["details"] == {}


def test_register_weak_password_returns_weak_password_code(monkeypatch):
    client, store = build_auth_client(monkeypatch)

    response = client.post(
        "/register",
        json={"username": "alice", "password": WEAK_SHORT_PASSWORD},
    )

    assert response.status_code == 400
    error = _error_envelope(response)
    assert error["code"] == "WEAK_PASSWORD"
    assert error["details"] == {}
    assert store.users_by_username == {}


def test_login_valid_credentials(monkeypatch):
    client, _store = build_auth_client(monkeypatch)
    client.post("/register", json={"username": "alice", "password": STRONG_PASSWORD})

    response = client.post(
        "/login",
        json={"username": "alice", "password": STRONG_PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["user_id"] == 1


def test_login_wrong_password_returns_generic_invalid_credentials(monkeypatch):
    client, _store = build_auth_client(monkeypatch)
    client.post("/register", json={"username": "alice", "password": STRONG_PASSWORD})

    response = client.post(
        "/login",
        json={"username": "alice", "password": "wrongpass1"},
    )

    assert response.status_code == 401
    error = _error_envelope(response)
    assert error["code"] == "UNAUTHORIZED"
    assert error["message"] == "invalid credentials"


def test_login_unknown_username_returns_same_generic_message(monkeypatch):
    client, _store = build_auth_client(monkeypatch)

    response = client.post(
        "/login",
        json={"username": "missing", "password": STRONG_PASSWORD},
    )

    assert response.status_code == 401
    error = _error_envelope(response)
    assert error["message"] == "invalid credentials"


def test_protected_route_without_session_returns_401(monkeypatch):
    client, _store = build_auth_client(monkeypatch)

    response = client.get("/protected")

    assert response.status_code == 401
    error = _error_envelope(response)
    assert error["code"] == "UNAUTHORIZED"


def test_change_password_wrong_current_password(monkeypatch):
    client, _store = build_auth_client(monkeypatch)
    client.post("/register", json={"username": "alice", "password": STRONG_PASSWORD})
    client.post("/login", json={"username": "alice", "password": STRONG_PASSWORD})

    response = client.post(
        "/change_password",
        json={"current_password": "wrongpass1", "new_password": "newpass12"},
    )

    assert response.status_code == 401
    error = _error_envelope(response)
    assert error["code"] == "UNAUTHORIZED"


def test_change_password_weak_new_password_returns_weak_password_code(monkeypatch):
    client, _store = build_auth_client(monkeypatch)
    client.post("/register", json={"username": "alice", "password": STRONG_PASSWORD})
    client.post("/login", json={"username": "alice", "password": STRONG_PASSWORD})

    response = client.post(
        "/change_password",
        json={
            "current_password": STRONG_PASSWORD,
            "new_password": WEAK_NO_DIGIT_PASSWORD,
        },
    )

    assert response.status_code == 400
    error = _error_envelope(response)
    assert error["code"] == "WEAK_PASSWORD"


def test_register_missing_fields_use_canonical_envelope():
    with pytest.raises(HTTPException) as raised:
        register(UserAuth(username="", password=""))

    assert isinstance(raised.value.detail, dict)
    assert raised.value.detail["code"]
    assert raised.value.detail["message"]
    assert raised.value.detail["details"] == {}


def test_change_password_missing_fields_use_canonical_envelope():
    with pytest.raises(HTTPException) as raised:
        change_password(
            ChangePasswordPayload(current_password="", new_password=""),
            user_id=1,
        )

    assert isinstance(raised.value.detail, dict)
    assert raised.value.detail["code"]
    assert raised.value.detail["message"]
    assert raised.value.detail["details"] == {}


def test_login_sets_httponly_secure_lax_session_cookie(monkeypatch):
    client, _store = build_auth_client(monkeypatch)
    client.post("/register", json={"username": "alice", "password": STRONG_PASSWORD})

    response = client.post(
        "/login",
        json={"username": "alice", "password": STRONG_PASSWORD},
    )

    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie
    assert "max-age=86400" in cookie
