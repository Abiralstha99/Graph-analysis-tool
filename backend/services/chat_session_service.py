"""Persist chat conversations in the chat_sessions table."""

from __future__ import annotations

import json


def save_session(db, conversation_id: str, user_id: int, messages: list) -> None:
    cur = db.cursor()
    cur.execute(
        "INSERT INTO chat_sessions (id, user_id, messages) VALUES (%s, %s, %s)",
        (conversation_id, user_id, json.dumps(messages)),
    )
    db.commit()


def get_session(db, conversation_id: str, user_id: int):
    cur = db.cursor(dictionary=True)
    cur.execute(
        "SELECT messages FROM chat_sessions WHERE id = %s AND user_id = %s",
        (conversation_id, user_id),
    )
    row = cur.fetchone()
    if row is None:
        return None
    messages = row["messages"]
    if isinstance(messages, (bytes, bytearray)):
        messages = messages.decode("utf-8")
    if isinstance(messages, str):
        return json.loads(messages)
    return list(messages)


def delete_session(db, conversation_id: str, user_id: int) -> None:
    cur = db.cursor()
    cur.execute(
        "DELETE FROM chat_sessions WHERE id = %s AND user_id = %s",
        (conversation_id, user_id),
    )
    db.commit()


def count_sessions(db) -> int:
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM chat_sessions")
    row = cur.fetchone()
    if row is None:
        return 0
    if isinstance(row, dict):
        return int(next(iter(row.values())))
    return int(row[0])
