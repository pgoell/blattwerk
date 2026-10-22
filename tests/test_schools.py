"""School seats, the invoice PDF and the public processor list (issue #91).

Pack prices, the seller's tax number and the AVV text are Pascal's. These tests
supply fixture figures and a fixture PDF, and they expect the product to keep
none of its own.
"""

import io
from pathlib import Path

from fastapi.testclient import TestClient
from playwright.sync_api import expect
from pypdf import PdfReader
from ui import reload

from blattwerk import auth, db
from blattwerk.app import app

PASSWORD = "richtig-geheim"
EMPTY = {"pages": [{"blocks": []}], "guides": {"x": [], "y": []}, "grid": 0}
ORDER = {
    "name": "Nordschule",
    "street": "Waldweg 1",
    "postcode": "60311",
    "city": "Frankfurt",
    "country": "Deutschland",
    "seats": 2,
}
# Fixture commercial terms. Not a pack price and not Pascal's tax number.
ISSUED = {
    "amount_cents": 100,
    "vat_rate": 0,
    "vat_note": "Keine Umsatzsteuer ausgewiesen.",
    "tax_number": "12/345/67890",
    "seller_address": "Testweg 1, 12345 Teststadt",
    "due": "2099-02-01",
}


def client(email, admin=False):
    """A client logged in as a new user. https, or the Secure cookie is not sent back."""
    made = TestClient(app, base_url="https://testserver")
    body = {"token": auth.new_link(db.open_db(), admin=admin), "email": email, "password": PASSWORD}
    assert made.post("/api/signup", json=body).status_code == 200
    return made


def order(head, seats=2):
    res = head.post("/api/school", json={**ORDER, "seats": seats})
    assert res.status_code == 200, res.text
    return res.json()


def open_year(pascal, school_id, when="2099-01-01"):
    res = pascal.post(f"/api/admin/schools/{school_id}/year", json={"year_ends": when})
    assert res.status_code == 200, res.text
    return res.json()


def test_a_teacher_orders_a_school_and_gets_no_price():
    head = client("leitung@example.com")
    school = order(head)
    assert school["name"] == "Nordschule"
    assert school["seats"] == 2
    assert school["taken"] == 1
    assert school["active"] is False
    assert school["year_ends"] is None
    assert school["head"] is True
    assert school["invoices"][0]["status"] == "draft"
    assert "amount_cents" not in school["invoices"][0]
    assert "99" not in school["invoices"][0]["number"]
    again = head.post("/api/school", json=ORDER)
    assert again.status_code == 409


def test_invite_seats_a_new_teacher_and_an_existing_one():
    head = client("leitung@example.com")
    pascal = client("pascal@example.com", admin=True)
    school = order(head, seats=3)
    assert head.post("/api/school/invites", json={"email": "neu@example.com"}).status_code == 409
    open_year(pascal, school["id"])

    token = head.post("/api/school/invites", json={"email": "neu@example.com"}).json()["token"]
    guest = TestClient(app, base_url="https://testserver")
    signed = guest.post(
        "/api/school/signup",
        json={"token": token, "email": "neu@example.com", "password": PASSWORD},
    )
    assert signed.status_code == 200, signed.text
    assert guest.get("/api/school").json()["head"] is False
    assert guest.get("/api/school").json()["active"] is True

    other = client("da@example.com")
    link = head.post("/api/school/invites", json={"email": "da@example.com"}).json()["token"]
    assert other.post("/api/school/accept", json={"token": link}).status_code == 200
    assert other.get("/api/school").json()["name"] == "Nordschule"
    # The link was one use.
    assert other.post("/api/school/accept", json={"token": link}).status_code == 404


def test_remove_keeps_her_sheets():
    head = client("leitung@example.com")
    pascal = client("pascal@example.com", admin=True)
    school = order(head)
    open_year(pascal, school["id"])
    other = client("da@example.com")
    link = head.post("/api/school/invites", json={"email": "da@example.com"}).json()["token"]
    assert other.post("/api/school/accept", json={"token": link}).status_code == 200
    made = other.post("/api/sheets", json={"title": "Eins", "doc": EMPTY})
    assert made.status_code == 200, made.text
    gone = head.delete(f"/api/school/members/{other.get('/api/me').json()['id']}")
    assert gone.status_code == 200, gone.text
    assert other.get("/api/school").status_code == 404
    assert other.get(f"/api/sheets/{made.json()['id']}").json()["title"] == "Eins"
    # The head's own seat is not a member she can drop.
    assert head.delete(f"/api/school/members/{head.get('/api/me').json()['id']}").status_code == 409


def test_seat_limit_counts_the_head_and_an_open_invite():
    head = client("leitung@example.com")
    pascal = client("pascal@example.com", admin=True)
    school = order(head, seats=2)
    open_year(pascal, school["id"])
    first = head.post("/api/school/invites", json={"email": "a@example.com"})
    assert first.status_code == 200, first.text
    assert head.post("/api/school/invites", json={"email": "b@example.com"}).status_code == 409
    # A wrong invite would block the only free seat for a week. Taking it back frees the seat.
    assert (
        head.post("/api/school/invites/revoke", json={"email": "a@example.com"}).status_code == 200
    )
    second = head.post("/api/school/invites", json={"email": "b@example.com"})
    assert second.status_code == 200, second.text
    guest = TestClient(app, base_url="https://testserver")
    assert (
        guest.post(
            "/api/school/signup",
            json={"token": second.json()["token"], "email": "b@example.com", "password": PASSWORD},
        ).status_code
        == 200
    )
    assert head.post("/api/school/invites", json={"email": "c@example.com"}).status_code == 409
    assert head.get("/api/school").json()["taken"] == 2


def test_a_year_that_has_ended_seats_nobody_and_an_extension_seats_them_again():
    head = client("leitung@example.com")
    pascal = client("pascal@example.com", admin=True)
    # One seat stays free, so a refusal is the year and not the seat count.
    school = order(head, seats=3)
    open_year(pascal, school["id"])
    other = client("da@example.com")
    link = head.post("/api/school/invites", json={"email": "da@example.com"}).json()["token"]
    assert other.post("/api/school/accept", json={"token": link}).status_code == 200
    made = other.post("/api/sheets", json={"title": "Eins", "doc": EMPTY})
    ended = open_year(pascal, school["id"], when="2000-01-01")
    assert ended["active"] is False
    assert other.get("/api/school").json()["active"] is False
    assert head.post("/api/school/invites", json={"email": "neu@example.com"}).status_code == 409
    assert other.get(f"/api/sheets/{made.json()['id']}").json()["title"] == "Eins"
    extended = open_year(pascal, school["id"], when="2099-06-01")
    assert extended["active"] is True
    assert other.get("/api/school").json()["active"] is True
    assert head.post("/api/school/invites", json={"email": "neu@example.com"}).status_code == 200


def test_the_invoice_pdf_shows_only_what_pascal_wrote():
    head = client("leitung@example.com")
    pascal = client("pascal@example.com", admin=True)
    school = order(head, seats=5)
    invoice = school["invoices"][0]
    early = head.get(f"/api/school/invoices/{invoice['id']}")
    assert early.status_code == 409
    issued = pascal.post(f"/api/admin/invoices/{invoice['id']}", json=ISSUED)
    assert issued.status_code == 200, issued.text
    res = head.get(f"/api/school/invoices/{invoice['id']}")
    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("application/pdf")
    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(res.content)).pages)
    assert "Nordschule" in text
    assert "Waldweg 1" in text
    assert "60311" in text
    assert "Frankfurt" in text
    assert invoice["number"] in text
    assert "12/345/67890" in text
    assert "Testweg 1, 12345 Teststadt" in text
    assert "Pascal Göllner" in text
    assert "Betrag: 1,00 EUR" in text
    assert "Keine Umsatzsteuer ausgewiesen." in text
    assert "01.02.2099" in text
    assert "99,00" not in text
    assert "169,00" not in text
    assert "229,00" not in text
    # 19 % is worked out from the rate Pascal sent, on top of the net amount.
    rated = {
        **ISSUED,
        "amount_cents": 10000,
        "vat_rate": 1900,
        "vat_note": "",
    }
    nxt = pascal.post(f"/api/admin/schools/{school['id']}/invoices", json={})
    assert nxt.status_code == 409
    paid = pascal.post(f"/api/admin/invoices/{invoice['id']}/paid")
    assert paid.status_code == 200, paid.text
    con = db.open_db()
    try:
        expected = con.execute("SELECT date('now', '+1 year')").fetchone()[0]
    finally:
        con.close()
    assert paid.json()["year_ends"] == expected
    nxt = pascal.post(f"/api/admin/schools/{school['id']}/invoices")
    assert nxt.status_code == 200, nxt.text
    assert pascal.post(f"/api/admin/invoices/{nxt.json()['id']}", json=rated).status_code == 200
    second = head.get(f"/api/school/invoices/{nxt.json()['id']}")
    rated_text = "\n".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(second.content)).pages
    )
    assert "Netto: 100,00 EUR" in rated_text
    assert "Umsatzsteuer 19,00 %: 19,00 EUR" in rated_text
    assert "Brutto: 119,00 EUR" in rated_text


def test_mark_paid_keeps_a_year_pascal_already_set():
    head = client("leitung@example.com")
    pascal = client("pascal@example.com", admin=True)
    school = order(head)
    open_year(pascal, school["id"], when="2099-06-01")
    invoice = school["invoices"][0]["id"]
    assert pascal.post(f"/api/admin/invoices/{invoice}", json=ISSUED).status_code == 200
    paid = pascal.post(f"/api/admin/invoices/{invoice}/paid")
    assert paid.status_code == 200, paid.text
    assert paid.json()["year_ends"] == "2099-06-01"
    assert pascal.post(f"/api/admin/invoices/{invoice}/paid").status_code == 409


def test_the_avv_is_the_file_pascal_pointed_at(tmp_path, monkeypatch):
    head = client("leitung@example.com")
    order(head)
    missing = head.get("/api/school/avv")
    assert missing.status_code == 404
    fixture = Path(tmp_path) / "avv.pdf"
    fixture.write_bytes(b"%PDF-1.4 fixture, not a contract\n")
    monkeypatch.setenv("BLATTWERK_AVV", str(fixture))
    got = head.get("/api/school/avv")
    assert got.status_code == 200
    assert got.content == fixture.read_bytes()
    stranger = client("andere@example.com")
    assert stranger.get("/api/school/avv").status_code == 404


def test_deleting_the_head_drops_the_school_and_keeps_a_teachers_sheet():
    head = client("leitung@example.com")
    pascal = client("pascal@example.com", admin=True)
    school = order(head)
    open_year(pascal, school["id"])
    other = client("da@example.com")
    link = head.post("/api/school/invites", json={"email": "da@example.com"}).json()["token"]
    assert other.post("/api/school/accept", json={"token": link}).status_code == 200
    made = other.post("/api/sheets", json={"title": "Eins", "doc": EMPTY})
    assert head.delete("/api/me").status_code == 200
    assert other.get("/api/school").status_code == 404
    assert other.get(f"/api/sheets/{made.json()['id']}").json()["title"] == "Eins"


def test_the_processor_list_names_hetzner_and_cloudflare():
    text = TestClient(app).get("/auftragsverarbeiter").text
    assert text.count("Hetzner Online GmbH") == 1
    assert "Deutschland" in text
    assert "Cloudflare, Inc." in text
    assert "USA" in text
    assert "/datenschutz" in text
    # Claude is the teacher's own contract on the privacy page, not a host we list here.
    assert "Anthropic" not in text
    assert "AVV" not in text


def test_a_stranger_and_a_logged_out_teacher_get_nothing():
    head = client("leitung@example.com")
    school = order(head)
    stranger = client("andere@example.com")
    assert stranger.post("/api/school/invites", json={"email": "x@example.com"}).status_code == 404
    assert stranger.get(f"/api/school/invoices/{school['invoices'][0]['id']}").status_code == 404
    assert stranger.get("/api/admin/schools").status_code == 404
    out = TestClient(app, base_url="https://testserver")
    assert out.get("/api/school").status_code == 401
    assert out.post("/api/school", json=ORDER).status_code == 401
    assert out.get("/api/admin/schools").status_code == 401


def test_the_school_page_takes_an_order_and_the_admin_sees_the_draft(browser, server):
    head = client("leitung@example.com")
    pascal = client("pascal@example.com", admin=True)
    context = browser.new_context()
    try:
        context.add_cookies([{"name": "session", "value": head.cookies["session"], "url": server}])
        page = context.new_page()
        page.goto(f"{server}/schule")
        expect(page.get_by_role("heading", name="Schule", exact=True)).to_be_visible()
        expect(page.get_by_text("Ein Platz gilt zu Hause wie in der Schule.")).to_be_visible()
        page.get_by_label("Name der Schule").fill("Nordschule")
        page.get_by_label("Straße").fill("Waldweg 1")
        page.get_by_label("Postleitzahl").fill("60311")
        page.get_by_label("Ort").fill("Frankfurt")
        page.get_by_label("Plätze").fill("2")
        page.get_by_role("button", name="Schule anlegen").click()
        expect(page.get_by_role("heading", name="Nordschule", exact=True)).to_be_visible()
        expect(page.get_by_text("ist noch nicht ausgestellt")).to_be_visible()
        expect(page.get_by_text("Der AVV liegt noch nicht vor.")).to_be_visible()
        expect(page.get_by_text("Einladen geht, sobald das Schuljahr läuft.")).to_be_visible()
        page.screenshot(path="/tmp/school-ordered.png")
        open_year(pascal, head.get("/api/school").json()["id"])
        reload(page, f"{server}/schule")
        page.get_by_label("E-Mail").fill("neu@example.com")
        page.get_by_role("button", name="Link erstellen").click()
        expect(page.locator(".link")).to_contain_text("/schulplatz/")
        page.screenshot(path="/tmp/school-invite.png")
    finally:
        context.close()

    admin_context = browser.new_context()
    try:
        admin_context.add_cookies(
            [{"name": "session", "value": pascal.cookies["session"], "url": server}]
        )
        admin = admin_context.new_page()
        admin.goto(f"{server}/admin")
        expect(admin.get_by_text("Nordschule, leitung@example.com")).to_be_visible()
        expect(admin.get_by_text("Entwurf")).to_be_visible()
        number = head.get("/api/school").json()["invoices"][0]["number"]
        admin.get_by_label("Netto in EUR").fill("1,00")
        admin.get_by_label("Umsatzsteuer in %").fill("0")
        admin.get_by_label("Hinweis zur Umsatzsteuer").fill("Keine Umsatzsteuer ausgewiesen.")
        admin.get_by_label("Steuernummer").fill("12/345/67890")
        admin.get_by_label("Deine Anschrift auf der Rechnung").fill("Testweg 1, 12345 Teststadt")
        admin.get_by_label("Fällig am").fill("2099-02-01")
        admin.get_by_role("button", name="Rechnung ausstellen").click()
        expect(admin.get_by_role("link", name=f"Rechnung {number}")).to_be_visible()
        expect(admin.get_by_label("Netto in EUR")).to_have_count(0)
        admin.screenshot(path="/tmp/admin-school.png")
    finally:
        admin_context.close()
