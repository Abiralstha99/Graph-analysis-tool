"""Auth request payloads."""

from pydantic import BaseModel


class UserAuth(BaseModel):
    username: str
    password: str


class ChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str
