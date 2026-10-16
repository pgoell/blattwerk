"""Accounts: invite-only sign-up, login, password reset links and the admin calls."""

import hashlib
import hmac
import logging
import secrets
import shutil
import sqlite3
import time
from contextlib import suppress
from pathlib import Path
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from blattwerk import db
from blattwerk.db import Con, Id

SESSION_DAYS = 90
LINK_DAYS = 7
# Login tries allowed per email and per IP in one window.
TRIES = 10
WINDOW = 15 * 60
# Tries to delete a deleted account's folder, and the seconds between two of them.
DELETE_TRIES = 3
DELETE_WAIT = 0.2

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


def token_user(con: sqlite3.Connection, request: Request, token: str) -> sqlite3.Row:
    """The user an API token belongs to. A bad token is a try per IP: 429 after TRIES of them."""
    key = f"token:{request.client.host if request.client else ''}"
    # Reads only, so a good token writes nothing here.
    tries = "SELECT count(*) FROM attempts WHERE key = ? AND created > datetime('now', ?)"
    if con.execute(tries, (key, f"-{WINDOW} seconds")).fetchone()[0] >= TRIES:
        raise HTTPException(429)
    row = None
    parts = token.split("_", 2)
    if len(parts) == 3 and parts[0] == "bt" and db.ID.fullmatch(parts[1]) and int(parts[1]) < 2**63:
        row = con.execute(
            "SELECT tokens.id AS token_id, tokens.hash, users.* FROM tokens"
            " JOIN users ON users.id = tokens.user_id WHERE tokens.id = ?",
            (int(parts[1]),),
        ).fetchone()
    if not row or not hmac.compare_digest(row["hash"], digest(token)):
        con.execute(
            "DELETE FROM attempts WHERE created <= datetime('now', ?)", (f"-{WINDOW} seconds",)
        )
        con.execute("INSERT INTO attempts (key) VALUES (?)", (key,))
        raise HTTPException(401)
    with suppress(sqlite3.Error):
        con.execute(
            "UPDATE tokens SET last_used = CURRENT_TIMESTAMP WHERE id = ?", (row["token_id"],)
        )
    return row


def current_teacher(
    request: Request, con: Con, session: Annotated[str | None, Cookie()] = None
) -> sqlite3.Row:
    # With an Authorization header the cookie is ignored: a bad token beside a good cookie is 401.
    header = request.headers.get("authorization")
    if header is None:
        return current_user(con, session)
    scheme, _, token = header.partition(" ")
    return token_user(con, request, token if scheme.lower() == "bearer" else "")


Teacher = Annotated[sqlite3.Row, Depends(current_teacher)]


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
    error = remove(folder)
    for _ in range(DELETE_TRIES - 1):
        if not error:
            break
        time.sleep(DELETE_WAIT)
        error = remove(folder)
    if error:
        # The account is gone either way. The row outlives a restart: each start tries again,
        # and the admin page shows it until the folder is gone.
        log.error("Could not delete %s", folder)
        try:
            con.execute(
                "INSERT INTO leftovers (user_id, error) VALUES (?, ?)"
                " ON CONFLICT (user_id) DO UPDATE SET error = excluded.error",
                (user["id"], error),
            )
        except sqlite3.Error:
            # The account is gone, so the answer stays 200; the log line above is the trace.
            log.exception("Could not remember the left over folder %s", folder)
    response.delete_cookie("session")
    return {}


class NewToken(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def stripped(cls, value: str) -> str:
        value = value.strip()
        if not 1 <= len(value) <= 80:
            raise ValueError("a name of 1 to 80 characters")
        return value


# Cookie only, like the admin calls: a token cannot mint or list tokens.
@router.post("/tokens")
def make_token(body: NewToken, user: User, con: Con) -> dict:
    # One transaction, so no row is left with an empty hash.
    con.execute("BEGIN IMMEDIATE")
    try:
        row = con.execute(
            "INSERT INTO tokens (user_id, hash, name) VALUES (?, '', ?) RETURNING id",
            (user["id"], body.name),
        ).fetchone()
        token = f"bt_{row['id']}_{secrets.token_urlsafe(32)}"
        # Only the hash is stored: this answer is the one place the token is shown.
        con.execute("UPDATE tokens SET hash = ? WHERE id = ?", (digest(token), row["id"]))
    except BaseException:
        con.execute("ROLLBACK")
        raise
    con.execute("COMMIT")
    made = con.execute("SELECT id, name, created, last_used FROM tokens WHERE id = ?", (row["id"],))
    return {**dict(made.fetchone()), "token": token}


@router.get("/tokens")
def tokens(user: User, con: Con) -> list[dict]:
    rows = con.execute(
        "SELECT id, name, created, last_used FROM tokens WHERE user_id = ? ORDER BY id DESC",
        (user["id"],),
    )
    return [dict(row) for row in rows]


@router.delete("/tokens/{token_id}")
def revoke(token_id: Id, user: User, con: Con) -> dict:
    cur = con.execute("DELETE FROM tokens WHERE id = ? AND user_id = ?", (token_id, user["id"]))
    if not cur.rowcount:
        raise HTTPException(404)
    return {}


def remove(folder: Path) -> str | None:
    """One try to delete a folder. Gives the first error, or None when the folder is gone."""
    errors = []
    # Past a file that will not go, so as much goes as can.
    shutil.rmtree(folder, onexc=lambda function, path, error: errors.append(error))
    if not folder.exists():
        return None
    return f"{type(errors[0]).__name__}: {errors[0]}" if errors else "The folder is still there"


def retry_leftovers() -> None:
    """At each start: tries the folders a delete left behind again."""
    # Also with no row to try: the open makes a new file's tables.
    con = db.open_db()
    try:
        # Never the folder of a living account, whatever a restored or hand-made row says.
        gone = "SELECT user_id FROM leftovers WHERE user_id NOT IN (SELECT id FROM users)"
        for (user_id,) in con.execute(gone).fetchall():
            error = remove(db.DATA_DIR / "users" / str(user_id))
            if error:
                # `since` stays: the alert tells how long the folder has been there.
                con.execute("UPDATE leftovers SET error = ? WHERE user_id = ?", (error, user_id))
            else:
                con.execute("DELETE FROM leftovers WHERE user_id = ?", (user_id,))
    finally:
        con.close()


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
    con.execute("DELETE FROM tokens WHERE user_id = ?", (user_id,))
    return start_session(con, response, user_id)


@router.get("/admin/users")
def users(admin: Admin, con: Con) -> list[dict]:
    rows = con.execute("SELECT * FROM users ORDER BY id")
    return [{**public(row), "created": row["created"]} for row in rows]


@router.get("/admin/leftovers")
def leftovers(admin: Admin, con: Con) -> list[dict]:
    rows = con.execute("SELECT * FROM leftovers ORDER BY since, user_id").fetchall()
    left = []
    for row in rows:
        if (db.DATA_DIR / "users" / str(row["user_id"])).exists():
            folder = f"users/{row['user_id']}"
            left.append({"folder": folder, "since": row["since"], "error": row["error"]})
        else:
            # Someone removed the folder by hand: the alert goes without a restart. A busy
            # database keeps the row for the next look.
            with suppress(sqlite3.Error):
                con.execute("DELETE FROM leftovers WHERE user_id = ?", (row["user_id"],))
    return left


@router.post("/admin/invites")
def invite(admin: Admin, con: Con) -> dict:
    return {"token": new_link(con)}


@router.post("/admin/users/{user_id}/reset")
def reset_link(user_id: Id, admin: Admin, con: Con) -> dict:
    if not con.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone():
        raise HTTPException(404)
    return {"token": new_link(con, user_id)}
