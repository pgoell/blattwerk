"""#90: a signed webhook sets a teacher's plan. No card data, no price, no provider."""

import hashlib
import hmac
import io
import json
import sqlite3
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from test_app import EMPTY, user

from blattwerk import db
from blattwerk.app import app

SECRET = "test-webhook-secret"
CARD = "4242424242424242"
YEAR = "2999-01-01"
NEXT = "3000-01-01"


def post_event(client, event, *, secret=SECRET, signature=None):
    raw = json.dumps(event).encode()
    if signature is None and secret is not None:
        signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Blattwerk-Signature"] = signature
    return client.post("/api/billing/webhook", content=raw, headers=headers)


def paid(client, event_id, user_id, until=YEAR):
    res = post_event(
        client, {"id": event_id, "type": "paid", "user_id": user_id, "paid_until": until}
    )
    assert res.status_code == 200, res.text
    return res


def me(client):
    return client.get("/api/me").json()


def stored_events():
    con = db.open_db()
    try:
        return [dict(row) for row in con.execute("SELECT * FROM billing_events ORDER BY rowid")]
    finally:
        con.close()


def test_a_new_account_is_free():
    account = me(user("a@example.com"))
    assert account["plan"] == "free"
    assert account["paid_until"] is None
    assert account["renewal"] == "none"


def test_webhook_is_missing_without_a_secret(monkeypatch):
    """No secret is configured in production until Pascal sets one, so the route stays shut."""
    monkeypatch.delenv("BLATTWERK_BILLING_WEBHOOK_SECRET", raising=False)
    client = user("a@example.com")
    res = post_event(
        client,
        {"id": "evt-paid", "type": "paid", "user_id": me(client)["id"], "paid_until": YEAR},
    )
    assert res.status_code == 404
    assert me(client)["plan"] == "free"


def test_webhook_paid_sets_the_plan_and_the_year(monkeypatch):
    monkeypatch.setenv("BLATTWERK_BILLING_WEBHOOK_SECRET", SECRET)
    client = user("a@example.com")
    user_id = me(client)["id"]
    res = paid(client, "evt-paid", user_id)
    assert res.json()["plan"] == "paid"
    assert res.json()["paid_until"] == YEAR
    assert res.json()["renewal"] == "active"
    assert me(client)["plan"] == "paid"
    assert me(client)["paid_until"] == YEAR
    again = paid(client, "evt-paid", user_id)
    assert again.json()["paid_until"] == YEAR
    assert len(stored_events()) == 1


def test_webhook_renewed_moves_the_year_forward(monkeypatch):
    monkeypatch.setenv("BLATTWERK_BILLING_WEBHOOK_SECRET", SECRET)
    client = user("a@example.com")
    user_id = me(client)["id"]
    paid(client, "evt-paid", user_id, "2998-01-01")
    res = post_event(
        client, {"id": "evt-renewed", "type": "renewed", "user_id": user_id, "paid_until": NEXT}
    )
    assert res.status_code == 200, res.text
    assert res.json()["plan"] == "paid"
    assert res.json()["paid_until"] == NEXT
    assert res.json()["renewal"] == "active"
    assert me(client)["paid_until"] == NEXT


def test_webhook_cancelled_keeps_the_year_already_paid(monkeypatch):
    monkeypatch.setenv("BLATTWERK_BILLING_WEBHOOK_SECRET", SECRET)
    client = user("a@example.com")
    user_id = me(client)["id"]
    paid(client, "evt-paid", user_id)
    # A cancel must not shorten the year the teacher already paid, whatever date rides along.
    res = post_event(
        client,
        {
            "id": "evt-cancelled",
            "type": "cancelled",
            "user_id": user_id,
            "paid_until": "2000-01-01",
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["plan"] == "paid"
    assert res.json()["paid_until"] == YEAR
    assert res.json()["renewal"] == "cancelled"
    assert me(client)["plan"] == "paid"
    assert me(client)["renewal"] == "cancelled"


def test_webhook_payment_failed_does_not_extend_the_year(monkeypatch):
    monkeypatch.setenv("BLATTWERK_BILLING_WEBHOOK_SECRET", SECRET)
    client = user("a@example.com")
    user_id = me(client)["id"]
    paid(client, "evt-paid", user_id)
    res = post_event(
        client,
        {
            "id": "evt-failed",
            "type": "payment_failed",
            "user_id": user_id,
            "paid_until": NEXT,
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["plan"] == "paid"
    assert res.json()["paid_until"] == YEAR
    assert res.json()["renewal"] == "payment_failed"
    assert me(client)["paid_until"] == YEAR
    assert me(client)["renewal"] == "payment_failed"


def test_webhook_replay_does_not_rewind_a_later_event(monkeypatch):
    monkeypatch.setenv("BLATTWERK_BILLING_WEBHOOK_SECRET", SECRET)
    client = user("a@example.com")
    user_id = me(client)["id"]
    paid(client, "evt-paid", user_id, "2998-01-01")
    post_event(
        client, {"id": "evt-renewed", "type": "renewed", "user_id": user_id, "paid_until": NEXT}
    )
    again = paid(client, "evt-paid", user_id, "2998-01-01")
    assert again.json()["paid_until"] == NEXT
    assert [row["id"] for row in stored_events()] == ["evt-paid", "evt-renewed"]


def test_webhook_rejects_a_bad_signature(monkeypatch):
    monkeypatch.setenv("BLATTWERK_BILLING_WEBHOOK_SECRET", SECRET)
    client = user("a@example.com")
    res = post_event(
        client,
        {"id": "evt-paid", "type": "paid", "user_id": me(client)["id"], "paid_until": YEAR},
        signature="0" * 64,
    )
    assert res.status_code == 401
    assert me(client)["plan"] == "free"
    assert stored_events() == []


def test_webhook_rejects_card_data(monkeypatch, data_dir):
    monkeypatch.setenv("BLATTWERK_BILLING_WEBHOOK_SECRET", SECRET)
    client = user("a@example.com")
    res = post_event(
        client,
        {
            "id": "evt-card",
            "type": "paid",
            "user_id": me(client)["id"],
            "paid_until": YEAR,
            "card": CARD,
        },
    )
    assert res.status_code == 422
    assert CARD not in res.text
    assert CARD.encode() not in (data_dir / "blattwerk.db").read_bytes()
    assert me(client)["plan"] == "free"


def test_webhook_for_an_unknown_account_changes_nothing(monkeypatch):
    monkeypatch.setenv("BLATTWERK_BILLING_WEBHOOK_SECRET", SECRET)
    client = user("a@example.com")
    res = post_event(
        client, {"id": "evt-missing", "type": "paid", "user_id": 99, "paid_until": YEAR}
    )
    assert res.status_code == 404
    assert stored_events() == []


def test_paid_without_an_end_date_is_refused(monkeypatch):
    monkeypatch.setenv("BLATTWERK_BILLING_WEBHOOK_SECRET", SECRET)
    client = user("a@example.com")
    res = post_event(client, {"id": "evt-open", "type": "paid", "user_id": me(client)["id"]})
    assert res.status_code == 422
    assert me(client)["plan"] == "free"


def test_the_last_day_of_the_paid_year_still_counts_and_the_next_does_not(monkeypatch):
    monkeypatch.setenv("BLATTWERK_BILLING_WEBHOOK_SECRET", SECRET)
    client = user("a@example.com")
    user_id = me(client)["id"]
    paid(client, "evt-paid", user_id)
    today = datetime.now(UTC).date()
    con = db.open_db()
    con.execute("UPDATE users SET paid_until = ? WHERE id = ?", (today.isoformat(), user_id))
    con.close()
    assert me(client)["plan"] == "paid"
    con = db.open_db()
    yesterday = (today - timedelta(days=1)).isoformat()
    con.execute("UPDATE users SET paid_until = ? WHERE id = ?", (yesterday, user_id))
    con.close()
    assert me(client)["plan"] == "free"
    assert me(client)["paid_until"] == yesterday


def sheet(client, title):
    return client.post("/api/sheets", json={"title": title, "doc": EMPTY})


def test_free_count_blocks_only_new_sheets_and_only_when_set(monkeypatch):
    monkeypatch.setenv("BLATTWERK_BILLING_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("BLATTWERK_FREE_SHEETS", "1")
    free = user("a@example.com")
    first = sheet(free, "Eins")
    assert first.status_code == 200
    blocked = sheet(free, "Zwei")
    assert blocked.status_code == 402
    assert "€" not in blocked.text
    assert "39" not in blocked.text
    sheet_id = first.json()["id"]
    assert free.get(f"/api/sheets/{sheet_id}").status_code == 200
    assert free.patch(f"/api/sheets/{sheet_id}", json={"title": "Umbenannt"}).status_code == 200
    assert free.post(f"/api/sheets/{sheet_id}/duplicate").status_code == 402
    # The count is sheets only. A template is not a new sheet.
    assert free.post("/api/templates", json={"name": "T", "doc": EMPTY}).status_code == 200
    paying = user("b@example.com")
    paid(paying, "evt-paid", me(paying)["id"])
    assert sheet(paying, "Eins").status_code == 200
    assert sheet(paying, "Zwei").status_code == 200


def test_without_a_free_count_a_teacher_can_keep_making_sheets(monkeypatch):
    monkeypatch.delenv("BLATTWERK_FREE_SHEETS", raising=False)
    client = user("a@example.com")
    assert [sheet(client, title).status_code for title in ("Eins", "Zwei", "Drei")] == [
        200,
        200,
        200,
    ]


def test_a_free_count_that_is_not_a_number_limits_nobody(monkeypatch):
    """A typo must not lock every free account out of new sheets."""
    monkeypatch.setenv("BLATTWERK_FREE_SHEETS", "fünf")
    client = user("a@example.com")
    assert sheet(client, "Eins").status_code == 200


def test_a_missing_sheet_stays_missing_when_the_free_count_is_zero(monkeypatch):
    monkeypatch.setenv("BLATTWERK_FREE_SHEETS", "0")
    client = user("a@example.com")
    assert sheet(client, "Eins").status_code == 402
    assert client.post("/api/sheets/1/duplicate").status_code == 404


def install_printer(monkeypatch):
    """The PDF route, without Chromium: a blank page, so a watermark would have to be added here."""
    from blattwerk import pdf

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    out = io.BytesIO()
    writer.write(out)
    raw = out.getvalue()

    class Page:
        def on(self, *args, **kwargs):
            return None

        def goto(self, url):
            return None

        def pdf(self, **kwargs):
            return raw

    class Browser:
        def new_page(self, **kwargs):
            return Page()

        def close(self):
            return None

    class Started:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        @property
        def chromium(self):
            return self

        def launch(self):
            return Browser()

    monkeypatch.setattr(pdf, "sync_playwright", lambda: Started())
    monkeypatch.setattr(pdf, "drawn", lambda *args, **kwargs: None)


def test_pdf_has_no_watermark_for_free_paid_and_a_lapsed_year(monkeypatch):
    monkeypatch.setenv("BLATTWERK_BILLING_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("BLATTWERK_FREE_SHEETS", "1")
    install_printer(monkeypatch)
    free = user("a@example.com")
    made = sheet(free, "Frei")
    assert made.status_code == 200
    paying = user("b@example.com")
    paid(paying, "evt-paid", me(paying)["id"])
    owned = sheet(paying, "Bezahlt")
    assert owned.status_code == 200
    extra = sheet(paying, "Noch eins")
    assert extra.status_code == 200
    con = db.open_db()
    con.execute("UPDATE users SET paid_until = '2000-01-01' WHERE id = ?", (me(paying)["id"],))
    con.close()
    assert me(paying)["plan"] == "free"
    # Over the free count, and the year is over: both sheets still open, and a third does not.
    assert paying.get(f"/api/sheets/{owned.json()['id']}").status_code == 200
    assert paying.get(f"/api/sheets/{extra.json()['id']}").status_code == 200
    assert sheet(paying, "Zu viel").status_code == 402
    for client, made_sheet in ((free, made), (paying, owned), (paying, extra)):
        res = client.get(f"/api/sheets/{made_sheet.json()['id']}/pdf")
        assert res.status_code == 200, res.text
        assert res.headers["content-type"] == "application/pdf"
        assert res.content.startswith(b"%PDF")
        folded = res.content.lower()
        assert b"watermark" not in folded
        assert b"wasserzeichen" not in folded


def test_an_old_account_keeps_its_rows_and_starts_free(data_dir):
    """A database from before the plan columns gains them, and the account stays."""
    con = sqlite3_connect(data_dir)
    con.execute(
        """CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            admin INTEGER NOT NULL DEFAULT 0,
            created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    con.execute("INSERT INTO users (email, password) VALUES ('a@x.de', 'x')")
    con.close()
    opened = db.open_db()
    try:
        row = opened.execute("SELECT email, plan, paid_until, renewal FROM users").fetchone()
    finally:
        opened.close()
    assert row["email"] == "a@x.de"
    assert row["plan"] == "free"
    assert row["paid_until"] is None
    assert row["renewal"] == "none"


def sqlite3_connect(data_dir):
    return sqlite3.connect(data_dir / "blattwerk.db", autocommit=True)


def test_signup_stays_invite_only():
    client = TestClient(app, base_url="https://testserver")
    res = client.post("/api/signup", json={"email": "a@example.com", "password": "richtig-geheim"})
    assert res.status_code == 422


def test_no_route_takes_a_card(data_dir):
    client = user("a@example.com")
    res = client.post("/api/billing/checkout", json={"card": CARD})
    # A POST with no route is 405: the catch-all page route is GET only.
    assert res.status_code == 405
    assert CARD not in res.text
    assert CARD.encode() not in (data_dir / "blattwerk.db").read_bytes()
