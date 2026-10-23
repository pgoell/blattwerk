"""A teacher's plan, set by a signed webhook. Blattomat never sees a card.

The provider, the price and the free count are not decided. Until a webhook secret is set the
route does not exist, and until ``BLATTWERK_FREE_SHEETS`` is a number nobody is limited. A paid
year runs through ``paid_until`` inclusive. Cancel and a failed payment leave that day where it
is: the year already paid stays, and it is not extended.
"""

import hashlib
import hmac
import json
import os
import re
import sqlite3
from datetime import UTC, date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from blattwerk.db import Con

router = APIRouter(prefix="/api")
# A provider payload is a few fields. Anything larger is not an event.
MAX_BODY = 4096
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
# Shown if a free count is configured and the account is past it. No price: none is decided.
FULL = (
    "Das kostenlose Konto kann kein weiteres Blatt anlegen. "
    "Die vorhandenen bleiben lesbar und lassen sich als PDF speichern."
)
EventType = Literal["paid", "renewed", "cancelled", "payment_failed"]


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_.:-]{1,200}$")]
    type: EventType
    user_id: Annotated[int, Field(ge=1, lt=2**63)]
    paid_until: str | None = None


def today() -> str:
    return datetime.now(UTC).date().isoformat()


def cell(user: sqlite3.Row, name: str, default=None):
    """A column, or `default` when this database has not gained it yet."""
    try:
        return user[name]
    except IndexError:
        return default


def effective(user: sqlite3.Row, day: str | None = None) -> str:
    """``paid`` through the last day of the year, then ``free``. The column stays ``paid``."""
    until = cell(user, "paid_until")
    current = day or today()
    if cell(user, "plan", "free") == "paid" and isinstance(until, str) and until >= current:
        return "paid"
    return "free"


def view(user: sqlite3.Row) -> dict:
    renewal = cell(user, "renewal", "none") or "none"
    return {"plan": effective(user), "paid_until": cell(user, "paid_until"), "renewal": renewal}


def secret() -> str:
    return os.environ.get("BLATTWERK_BILLING_WEBHOOK_SECRET", "").strip()


def sign(key: str, raw: bytes) -> str:
    return hmac.new(key.encode(), raw, hashlib.sha256).hexdigest()


def free_count() -> int | None:
    """The number of sheets a free account may keep, or none when the count is not decided.

    Anything that is not a number, including a negative one, limits nobody: a typo must not lock
    every free account out of a new sheet.
    """
    raw = os.environ.get("BLATTWERK_FREE_SHEETS", "").strip()
    if not raw:
        return None
    try:
        count = int(raw)
    except ValueError:
        return None
    if count < 0:
        return None
    return count


def allow_new(con: sqlite3.Connection, user: sqlite3.Row) -> None:
    """Refuses a new sheet once a free account is at the configured count. Paid is not capped.

    Reading, renaming and the PDF stay open either way. With no count configured this does nothing.
    """
    cap = free_count()
    if cap is None or effective(user) == "paid":
        return
    count = con.execute("SELECT count(*) FROM sheets WHERE user_id = ?", (user["id"],)).fetchone()[
        0
    ]
    if count >= cap:
        raise HTTPException(402, FULL)


def parse_day(value: str) -> str:
    if not DAY.fullmatch(value):
        raise HTTPException(422)
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise HTTPException(422) from None


def answer(event_id: str, user: sqlite3.Row) -> dict:
    return {"id": event_id, "user_id": user["id"], **view(user)}


def end_date(event: Event) -> str | None:
    """The day a paid or renewed event grants. Cancel and a failed payment grant none."""
    if event.type not in ("paid", "renewed"):
        return None
    if event.paid_until is None:
        raise HTTPException(422)
    return parse_day(event.paid_until)


def apply(con: sqlite3.Connection, event: Event, paid_until: str | None) -> dict:
    con.execute("BEGIN IMMEDIATE")
    try:
        prior = con.execute(
            "SELECT user_id, type, paid_until FROM billing_events WHERE id = ?", (event.id,)
        ).fetchone()
        if prior:
            # The same id is the same event. A different body is a different event, and refused.
            same = (
                prior["user_id"] == event.user_id
                and prior["type"] == event.type
                and prior["paid_until"] == paid_until
            )
            if not same:
                raise HTTPException(409)
            con.execute("ROLLBACK")
            user = con.execute("SELECT * FROM users WHERE id = ?", (event.user_id,)).fetchone()
            if not user:
                raise HTTPException(404)
            return answer(event.id, user)
        user = con.execute("SELECT * FROM users WHERE id = ?", (event.user_id,)).fetchone()
        if not user:
            raise HTTPException(404)
        if event.type in ("paid", "renewed"):
            con.execute(
                "UPDATE users SET plan = 'paid', paid_until = ?, renewal = 'active' WHERE id = ?",
                (paid_until, event.user_id),
            )
        elif event.type == "cancelled":
            con.execute("UPDATE users SET renewal = 'cancelled' WHERE id = ?", (event.user_id,))
        else:
            # payment_failed. The year already paid is left where it is.
            con.execute(
                "UPDATE users SET renewal = 'payment_failed' WHERE id = ?", (event.user_id,)
            )
        con.execute(
            "INSERT INTO billing_events (id, user_id, type, paid_until) VALUES (?, ?, ?, ?)",
            (event.id, event.user_id, event.type, paid_until),
        )
        con.execute("COMMIT")
    except BaseException:
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise
    user = con.execute("SELECT * FROM users WHERE id = ?", (event.user_id,)).fetchone()
    return answer(event.id, user)


@router.post("/billing/webhook")
async def webhook(request: Request, con: Con) -> dict:
    # Absent until a secret is configured, so an open route cannot set a plan.
    key = secret()
    if not key:
        raise HTTPException(404)
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise HTTPException(413)
    got = request.headers.get("x-blattwerk-signature", "")
    if not hmac.compare_digest(got, sign(key, raw)):
        raise HTTPException(401)
    try:
        payload = json.loads(raw)
        event = Event.model_validate(payload)
    except json.JSONDecodeError, ValidationError:
        raise HTTPException(422) from None
    return apply(con, event, end_date(event))
