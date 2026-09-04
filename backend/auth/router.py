"""Authentication routes: register, login, logout, change password."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from mysql.connector import IntegrityError

from ..database import get_db_connection
from .dependencies import get_current_user_id
from .passwords import hash_password, verify_password
from .schemas import ChangePasswordPayload, UserAuth

router = APIRouter(tags=["auth"])


@router.post("/register")
def register(payload: UserAuth):
    username = payload.username.strip()
    password = payload.password
    if not username or not password:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="username and password required",
        )

    hashed = hash_password(password)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, hashed),
        )
        conn.commit()
        return {"status": "ok", "username": username}
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username already exists",
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred. Please try again.",
        )
    finally:
        if conn:
            conn.close()


@router.post("/login")
def login(payload: UserAuth, request: Request):
    username = payload.username.strip()
    password = payload.password
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username and password required",
        )

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, password FROM users WHERE username = %s",
            (username,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid credentials",
            )

        if not verify_password(password, row["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid credentials",
            )

        request.session["user_id"] = int(row["id"])
        return {"status": "ok", "user_id": row["id"]}
    finally:
        if conn:
            conn.close()


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"status": "ok"}


@router.post("/change_password")
def change_password(
    payload: ChangePasswordPayload,
    user_id: int = Depends(get_current_user_id),
):
    current_password = payload.current_password
    new_password = payload.new_password

    if not current_password or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both current and new passwords are required",
        )

    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters",
        )

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute(
            "SELECT password FROM users WHERE id = %s",
            (int(user_id),),
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not verify_password(current_password, row["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )

        new_hashed = hash_password(new_password)
        cur.execute(
            "UPDATE users SET password = %s WHERE id = %s",
            (new_hashed, int(user_id)),
        )
        conn.commit()

        return {"status": "ok", "message": "Password updated successfully"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred. Please try again.",
        )
    finally:
        if conn:
            conn.close()
