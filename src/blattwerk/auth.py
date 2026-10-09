"""Accounts: invite-only sign-up, login, password reset links and the admin calls."""

import hashlib
import logging
import secrets
import shutil
import sqlite3
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from blattwerk import db
from blattwerk.db import Con

SESSION_DAYS = 90
LINK_DAYS = 7
# Login tries allowed per email and per IP in one window.
TRIES = 10
WINDOW = 15 * 60

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")
hasher = PasswordHasher()
# Verified when the email is unknown, so a miss takes as long as a wrong password.
DUMMY = hasher.hash(secrets.token_hex())

Email = Annotated[str, Field(pattern=r"^\S+@\S+$", max_length=254)]
Password = Annotated[str, Field(min_length=8, max_length=200)]


class Login(BaseModel):
    email: str
    password: str


class Signup(BaseModel):
    token: str
    email: Email
    password: Password


class Reset(BaseModel):
    token: str
    password: Password


def digest(token: str) -> str:
    # Only hashes are stored, so a leaked database opens no session and no link.
    return hashlib.sha256(token.encode()).hexdigest()


def current_user(con: Con, session: Annotated[str | None, Cookie()] = None) -> sqlite3.Row:
    row = con.execute(
        "SELECT users.* FROM sessions JOIN users ON users.id = user_id"
        " WHERE token = ? AND expires > datetime('now')",
        (digest(session or ""),),
    ).fetchone()
    if not row:
        raise HTTPException(401)
    return row


User = Annotated[sqlite3.Row, Depends(current_user)]


def current_admin(user: User) -> sqlite3.Row:
    # 404, not 403: the admin pages do not exist for anyone else.
    if not user["admin"]:
        raise HTTPException(404)
    return user


Admin = Annotated[sqlite3.Row, Depends(current_admin)]


def limit(con: sqlite3.Connection, key: str) -> None:
    # Kept in the database, so a restart does not hand out fresh tries.
    con.execute("DELETE FROM attempts WHERE created <= datetime('now', ?)", (f"-{WINDOW} seconds",))
    if con.execute("SELECT count(*) FROM attempts WHERE key = ?", (key,)).fetchone()[0] >= TRIES:
        raise HTTPException(429)
    con.execute("INSERT INTO attempts (key) VALUES (?)", (key,))


def new_link(con: sqlite3.Connection, user_id: int | None = None, admin: bool = False) -> str:
    token = secrets.token_urlsafe(32)
    con.execute(
        "INSERT INTO links (token, user_id, admin) VALUES (?, ?, ?)",
        (digest(token), user_id, admin),
    )
    return token


def take_link(con: sqlite3.Connection, token: str, invite: bool) -> sqlite3.Row:
    rows = con.execute(
        "DELETE FROM links WHERE token = ? AND (user_id IS NULL) = ?"
        f" AND created > datetime('now', '-{LINK_DAYS} days') RETURNING user_id, admin",
        (digest(token), invite),
    ).fetchall()
    if not rows:
        raise HTTPException(404)
    return rows[0]


def start_session(con: sqlite3.Connection, response: Response, user_id: int) -> dict:
    token = secrets.token_urlsafe(32)
    con.execute(
        f"INSERT INTO sessions VALUES (?, ?, datetime('now', '+{SESSION_DAYS} days'))",
        (digest(token), user_id),
    )
    response.set_cookie(
        "session",
        token,
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return public(con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())


def public(user: sqlite3.Row) -> dict:
    return {"id": user["id"], "email": user["email"], "admin": bool(user["admin"])}


@router.post("/login")
def login(body: Login, request: Request, response: Response, con: Con) -> dict:
    email = body.email.strip().lower()
    limit(con, f"email:{email}")
    limit(con, f"ip:{request.client.host if request.client else ''}")
    row = con.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    try:
        hasher.verify(row["password"] if row else DUMMY, body.password)
    except VerificationError:
        raise HTTPException(401) from None
    if not row:
        raise HTTPException(401)
    return start_session(con, response, row["id"])


@router.post("/logout")
def logout(response: Response, con: Con, session: Annotated[str | None, Cookie()] = None) -> dict:
    con.execute("DELETE FROM sessions WHERE token = ?", (digest(session or ""),))
    response.delete_cookie("session")
    return {}


@router.get("/me")
def me(user: User) -> dict:
    return public(user)


@router.delete("/me")
def delete_account(user: User, response: Response, con: Con) -> dict:
    con.execute("DELETE FROM users WHERE id = ?", (user["id"],))
    folder = db.DATA_DIR / "users" / str(user["id"])
    # Past a file that will not go, so as much goes as can.
    shutil.rmtree(folder, ignore_errors=True)
    if folder.exists():
        # The account is gone either way; the log is the only trace of what stayed on disk.
        log.error("Could not delete %s", folder)
    response.delete_cookie("session")
    return {}


def retry_leftovers() -> None:
    """At each start: tries the folders a delete left behind again."""
    db.open_db().close()


@router.post("/signup")
def signup(body: Signup, response: Response, con: Con) -> dict:
    # One transaction, so an email that is taken does not use up the invite.
    con.execute("BEGIN")
    try:
        link = take_link(con, body.token, invite=True)
        user_id = con.execute(
            "INSERT INTO users (email, password, admin) VALUES (?, ?, ?)",
            (body.email.lower(), hasher.hash(body.password), link["admin"]),
        ).lastrowid
    except sqlite3.IntegrityError:
        con.execute("ROLLBACK")
        raise HTTPException(409) from None
    except HTTPException:
        con.execute("ROLLBACK")
        raise
    con.execute("COMMIT")
    assert user_id is not None
    return start_session(con, response, user_id)


@router.post("/reset")
def reset(body: Reset, response: Response, con: Con) -> dict:
    user_id = take_link(con, body.token, invite=False)["user_id"]
    con.execute("UPDATE users SET password = ? WHERE id = ?", (hasher.hash(body.password), user_id))
    con.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    return start_session(con, response, user_id)


@router.get("/admin/users")
def users(admin: Admin, con: Con) -> list[dict]:
    rows = con.execute("SELECT * FROM users ORDER BY id")
    return [{**public(row), "created": row["created"]} for row in rows]


@router.post("/admin/invites")
def invite(admin: Admin, con: Con) -> dict:
    return {"token": new_link(con)}


@router.post("/admin/users/{user_id}/reset")
def reset_link(user_id: int, admin: Admin, con: Con) -> dict:
    if not con.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone():
        raise HTTPException(404)
    return {"token": new_link(con, user_id)}
