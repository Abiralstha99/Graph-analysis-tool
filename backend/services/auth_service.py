"""Auth helpers: password strength rules used by register and change-password."""

from fastapi import HTTPException, status


def validate_password_strength(password: str) -> None:
    if len(password) < 8 or not any(character.isdigit() for character in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "WEAK_PASSWORD",
                "message": "Password must be at least 8 characters and contain at least one digit",
                "details": {},
            },
        )
