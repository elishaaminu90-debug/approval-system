"""Approval System HTTP API endpoints.

This module exposes a small demo API used by the frontend demo and tests.
"""

import sqlite3
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.approval_system import (
    init_db,
    create_user,
    send_letter,
    list_pending_for_role,
    list_all_letters,
    act_on_letter,
    get_letter,
    resend_letter,
)

DB_PATH = "approval.db"

init_db(DB_PATH)

app = FastAPI(title="Approval System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateUserIn(BaseModel):
    """Payload for creating a user."""
    name: str
    role: str


class SendLetterIn(BaseModel):
    """Payload for sending a letter."""
    sender_id: int
    title: str
    body: str


class ActIn(BaseModel):
    """Payload for acting on (approve/reject) a step."""
    letter_id: int
    actor_name: str
    actor_role: str
    action: str
    comments: Optional[str] = None
    recommendations: Optional[str] = None


@app.get("/api/users")
def get_users():
    """Return all users from the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = None
    cur = conn.cursor()
    cur.execute("SELECT id, name, role FROM users ORDER BY role, name")
    rows = cur.fetchall()
    conn.close()
    users = [{"id": r[0], "name": r[1], "role": r[2]} for r in rows]
    return users


@app.post("/api/users")
def post_user(payload: CreateUserIn):
    """Create a user from payload and return its id."""
    try:
        uid = create_user(DB_PATH, payload.name, payload.role)
        return {"id": uid, "name": payload.name, "role": payload.role}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/send")
def post_send(payload: SendLetterIn):
    """Send a new letter and return its id."""
    try:
        lid = send_letter(DB_PATH, payload.sender_id, payload.title, payload.body)
        return {"id": lid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/pending")
def get_pending(role: str):
    """List pending approvals for a role."""
    try:
        rows = list_pending_for_role(DB_PATH, role)
        return rows
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/letters")
def get_letters():
    """Return all letters."""
    return list_all_letters(DB_PATH)


@app.get("/api/letter/{letter_id}")
def get_letter_endpoint(letter_id: int):
    """Return a letter and its steps."""
    try:
        return get_letter(DB_PATH, letter_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    """Delete a user by ID."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return {"status": "deleted", "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/act")
def post_act(payload: ActIn):
    """Actor approves or rejects a letter's current step."""
    # Ensure actor exists (create if missing)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = None
    cur = conn.cursor()
    query = "SELECT id FROM users WHERE name = ? AND role = ?"
    params = (payload.actor_name, payload.actor_role)
    cur.execute(query, params)
    found = cur.fetchone()
    conn.close()

    if found:
        actor_id = found[0]
    else:
        # create user
        try:
            actor_id = create_user(DB_PATH, payload.actor_name, payload.actor_role)
        except Exception as exc:
            # if creation fails (e.g., invalid role), return error
            _msg = "Cannot create actor user; invalid role or duplicate"
            raise HTTPException(status_code=400, detail=_msg) from exc

    try:
        result = act_on_letter(
            DB_PATH,
            payload.letter_id,
            actor_id,
            payload.action,
            payload.comments,
            payload.recommendations,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class ResendIn(BaseModel):
    """Payload to resend a previously rejected letter."""
    letter_id: int
    sender_id: int
    title: str
    body: str


@app.post("/api/resend")
def post_resend(payload: ResendIn):
    """Allow the sender to update and resend a rejected letter."""
    try:
        _lid = payload.letter_id
        _sid = payload.sender_id
        _title = payload.title
        _body = payload.body
        resend_letter(DB_PATH, _lid, _sid, _title, _body)
        return {"status": "resent", "letter_id": _lid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/notifications")
def get_notifications():
    """Return recent notifications (stubbed)."""
    # Stub: in a real app this would query a notification store or send email
    return [{"message": "No new notifications"}]


@app.put("/api/users/{user_id}/password")
def reset_password(user_id: int):
    """Reset a user's password to the default (demo only)."""
    try:
        # Note: This is a demo API. In production, would store hashed passwords.
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        user = cur.fetchone()
        conn.close()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {"status": "reset", "user_id": user_id, "default_password": "student123"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
