import pytest
from fastapi import HTTPException, Request

from backend.middleware.auth import require_auth


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