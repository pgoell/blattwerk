"""A school, its seats and the invoice Pascal fills in by hand.

No pack price, no tax number and no AVV text live here. Pascal writes the
commercial lines onto the invoice, and the AVV is a file he points at with
BLATTWERK_AVV. A seat is the same account at home and at school: nothing here
reads an address of the network.
"""

import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, field_validator, model_validator

from blattwerk import auth
from blattwerk.auth import Admin, Email, Password, User
from blattwerk.db import Con, Id

# The name and the mail on the invoice are the ones the Impressum already prints.
SELLER = "Pascal Göllner"
SELLER_MAIL = "hello@pgoell.com"
router = APIRouter(prefix="/api")
Line = Annotated[str, Field(min_length=1, max_length=120)]


class Order(BaseModel):
    name: Line
    street: Line
    postcode: Line
    city: Line
    country: Line
    seats: int = Field(ge=1, le=500)

    @field_validator("name", "street", "postcode", "city", "country")
    @classmethod
    def one_line(cls, value: str) -> str:
        value = " ".join(value.split())
        if not 1 <= len(value) <= 120:
            raise ValueError("1 to 120 characters")
        return value


class Invite(BaseModel):
    email: Email

    @field_validator("email")
    @classmethod
    def lower(cls, value: str) -> str:
        return value.strip().lower()


class Accept(BaseModel):
    token: str = Field(max_length=200)


class SchoolSignup(Accept):
    email: Email
    password: Password

    @field_validator("email")
    @classmethod
    def lower(cls, value: str) -> str:
        return value.strip().lower()


class Issued(BaseModel):
    # Net cents. The gross and the VAT are worked out from this and `vat_rate`.
    amount_cents: int = Field(ge=0, le=100_000_000)
    # Basis points: 1900 is 19 %. 0 means Pascal's `vat_note` is the whole VAT line.
    vat_rate: int = Field(ge=0, le=10000)
    vat_note: str = ""
    tax_number: str
    seller_address: str
    due: str

    @model_validator(mode="after")
    def commercial(self) -> Issued:
        self.vat_note = self.vat_note.strip()
        self.tax_number = self.tax_number.strip()
        self.seller_address = " ".join(self.seller_address.split())
        if not 1 <= len(self.tax_number) <= 40:
            raise ValueError("a tax number")
        if not 1 <= len(self.seller_address) <= 120:
            raise ValueError("an address")
        if len(self.vat_note) > 200:
            raise ValueError("a shorter VAT note")
        if self.vat_rate == 0 and not self.vat_note:
            raise ValueError("a VAT note")
        try:
            found = date.fromisoformat(self.due)
        except ValueError:
            raise ValueError("a date") from None
        if self.due != found.isoformat():
            raise ValueError("a date")
        return self


class Year(BaseModel):
    year_ends: str

    @field_validator("year_ends")
    @classmethod
    def day(cls, value: str) -> str:
        try:
            found = date.fromisoformat(value)
        except ValueError:
            raise ValueError("a date") from None
        if value != found.isoformat():
            raise ValueError("a date")
        return value


def pdf_text(text: str) -> bytes:
    raw = text.encode("cp1252", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def pdf(lines: list[str]) -> bytes:
    """One A4 page in Helvetica. The standard font's WinAnsi encoding holds the umlauts."""
    chunks = [b"BT", b"/F1 11 Tf", b"50 790 Td", b"14 TL"]
    for index, line in enumerate(lines):
        if index:
            chunks.append(b"T*")
        chunks.append(b"(" + pdf_text(line) + b") Tj")
    chunks.append(b"ET")
    stream = b"\n".join(chunks)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842]"
        b" /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    start = len(out)
    out += f"xref\n0 {len(offsets)}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()
    return bytes(out)


def euro(cents: int) -> str:
    return f"{cents // 100},{cents % 100:02d} EUR"


def german_date(iso: str) -> str:
    year, month, day = iso[:10].split("-")
    return f"{day}.{month}.{year}"


def invoice_lines(row: sqlite3.Row) -> list[str]:
    net = row["amount_cents"]
    rate = row["vat_rate"]
    # Half up, away from the banker's rounding of round().
    vat = (net * rate + 5000) // 10000
    gross = net + vat
    places = f"{row['seats']} Platz" if row["seats"] == 1 else f"{row['seats']} Plätze"
    lines = [
        f"Rechnung {row['number']}",
        f"Rechnungsdatum: {german_date(row['issued'])}",
        "",
        SELLER,
        row["seller_address"],
        SELLER_MAIL,
        f"Steuernummer: {row['tax_number']}",
        "",
        "Rechnung an",
        row["name"],
        row["street"],
        f"{row['postcode']} {row['city']}",
        row["country"],
        "",
        f"Blattomat Schulplätze, {places}, ein Jahr",
    ]
    if rate:
        lines.append(f"Netto: {euro(net)}")
        lines.append(f"Umsatzsteuer {rate // 100},{rate % 100:02d} %: {euro(vat)}")
        lines.append(f"Brutto: {euro(gross)}")
    else:
        lines.append(row["vat_note"])
        lines.append(f"Betrag: {euro(gross)}")
    if row["vat_note"] and rate:
        lines.append(row["vat_note"])
    lines.append(f"Fällig am: {german_date(row['due'])}")
    return lines


def avv_path() -> Path | None:
    raw = os.environ.get("BLATTWERK_AVV", "")
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_file() else None


@contextmanager
def locked(con: sqlite3.Connection):
    con.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        con.execute("ROLLBACK")
        raise
    else:
        con.execute("COMMIT")


def taken(con: sqlite3.Connection, school_id: int) -> int:
    return con.execute(
        "SELECT count(*) FROM school_seats WHERE school_id = ?", (school_id,)
    ).fetchone()[0]


def pending_count(con: sqlite3.Connection, school_id: int) -> int:
    return con.execute(
        "SELECT count(*) FROM school_invites WHERE school_id = ? AND created > datetime('now', ?)",
        (school_id, f"-{auth.LINK_DAYS} days"),
    ).fetchone()[0]


def active(con: sqlite3.Connection, year_ends: str | None) -> bool:
    if not year_ends:
        return False
    return bool(con.execute("SELECT ? >= date('now')", (year_ends,)).fetchone()[0])


def running(con: sqlite3.Connection, year_ends: str | None) -> None:
    if not active(con, year_ends):
        raise HTTPException(409, "Das Schuljahr läuft nicht.")


def invoice_list(con: sqlite3.Connection, school_id: int) -> list[dict]:
    rows = con.execute(
        "SELECT id, number, status FROM invoices WHERE school_id = ? ORDER BY id", (school_id,)
    )
    return [dict(row) for row in rows]


def member_list(con: sqlite3.Connection, school_id: int) -> list[dict]:
    rows = con.execute(
        "SELECT users.id, users.email FROM school_seats JOIN users ON users.id = user_id"
        " WHERE school_id = ? ORDER BY users.id",
        (school_id,),
    )
    return [dict(row) for row in rows]


def invite_list(con: sqlite3.Connection, school_id: int) -> list[dict]:
    rows = con.execute(
        "SELECT email FROM school_invites WHERE school_id = ? AND created > datetime('now', ?)"
        " ORDER BY email",
        (school_id, f"-{auth.LINK_DAYS} days"),
    )
    return [{"email": row["email"]} for row in rows]


def teacher_view(con: sqlite3.Connection, school: sqlite3.Row, user: sqlite3.Row) -> dict:
    head = school["admin_id"] == user["id"]
    body = {
        "id": school["id"],
        "name": school["name"],
        "street": school["street"],
        "postcode": school["postcode"],
        "city": school["city"],
        "country": school["country"],
        "seats": school["seats"],
        "taken": taken(con, school["id"]),
        "pending": pending_count(con, school["id"]),
        "year_ends": school["year_ends"],
        "active": active(con, school["year_ends"]),
        "head": head,
        "invoices": invoice_list(con, school["id"]),
        "avv": avv_path() is not None,
    }
    if head:
        body["members"] = member_list(con, school["id"])
        body["invites"] = invite_list(con, school["id"])
    return body


def admin_view(con: sqlite3.Connection, school_id: int) -> dict:
    row = con.execute(
        "SELECT schools.*, users.email AS admin_email FROM schools"
        " JOIN users ON users.id = schools.admin_id WHERE schools.id = ?",
        (school_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404)
    return {
        "id": row["id"],
        "name": row["name"],
        "street": row["street"],
        "postcode": row["postcode"],
        "city": row["city"],
        "country": row["country"],
        "seats": row["seats"],
        "taken": taken(con, row["id"]),
        "pending": pending_count(con, row["id"]),
        "year_ends": row["year_ends"],
        "active": active(con, row["year_ends"]),
        "admin_email": row["admin_email"],
        "invoices": invoice_list(con, row["id"]),
    }


def school_of(con: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return con.execute(
        "SELECT schools.* FROM schools JOIN school_seats ON school_seats.school_id = schools.id"
        " WHERE school_seats.user_id = ?",
        (user_id,),
    ).fetchone()


def head_school(con: sqlite3.Connection, user: sqlite3.Row) -> sqlite3.Row:
    row = con.execute("SELECT * FROM schools WHERE admin_id = ?", (user["id"],)).fetchone()
    if not row:
        raise HTTPException(404)
    return row


def fresh(con: sqlite3.Connection, token: str) -> sqlite3.Row | None:
    if not token or len(token) > 200:
        return None
    return con.execute(
        "SELECT school_invites.email, school_invites.school_id, schools.name, schools.year_ends,"
        " schools.seats, schools.admin_id FROM school_invites"
        " JOIN schools ON schools.id = school_invites.school_id"
        " WHERE school_invites.token = ? AND school_invites.created > datetime('now', ?)",
        (auth.digest(token), f"-{auth.LINK_DAYS} days"),
    ).fetchone()


def reserve(con: sqlite3.Connection, school_id: int, seats: int) -> None:
    if taken(con, school_id) + pending_count(con, school_id) >= seats:
        raise HTTPException(409, "Die Plätze sind belegt.")


def seat_free(con: sqlite3.Connection, school_id: int, seats: int) -> None:
    if taken(con, school_id) >= seats:
        raise HTTPException(409, "Die Plätze sind belegt.")


def not_seated(con: sqlite3.Connection, user_id: int) -> None:
    if con.execute("SELECT 1 FROM school_seats WHERE user_id = ?", (user_id,)).fetchone():
        raise HTTPException(409, "Du bist schon an einer Schule.")


def not_invited(con: sqlite3.Connection, school_id: int, email: str) -> None:
    if con.execute(
        "SELECT 1 FROM school_seats JOIN users ON users.id = user_id"
        " WHERE school_id = ? AND email = ?",
        (school_id, email),
    ).fetchone():
        raise HTTPException(409, "Diese Lehrkraft ist schon dabei.")
    if con.execute(
        "SELECT 1 FROM school_invites WHERE school_id = ? AND email = ?"
        " AND created > datetime('now', ?)",
        (school_id, email, f"-{auth.LINK_DAYS} days"),
    ).fetchone():
        raise HTTPException(409, "Diese E-Mail ist schon eingeladen.")


def new_invoice(con: sqlite3.Connection, school_id: int, seats: int) -> dict:
    row = con.execute(
        "INSERT INTO invoices (school_id, number, seats) VALUES (?, ?, ?) RETURNING id",
        (school_id, f"tmp-{secrets.token_hex(8)}", seats),
    ).fetchone()
    year = con.execute("SELECT strftime('%Y', 'now')").fetchone()[0]
    number = f"{year}-{row['id']:04d}"
    con.execute("UPDATE invoices SET number = ? WHERE id = ?", (number, row["id"]))
    return {"id": row["id"], "number": number, "status": "draft"}


def place(con: sqlite3.Connection, school_id: int, user_id: int, token: str) -> None:
    try:
        con.execute(
            "INSERT INTO school_seats (school_id, user_id) VALUES (?, ?)", (school_id, user_id)
        )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Du bist schon an einer Schule.") from None
    con.execute("DELETE FROM school_invites WHERE token = ?", (auth.digest(token),))


@router.post("/school")
def order(body: Order, user: User, con: Con) -> dict:
    with locked(con):
        not_seated(con, user["id"])
        try:
            school_id = con.execute(
                "INSERT INTO schools (name, street, postcode, city, country, admin_id, seats)"
                " VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id",
                (
                    body.name,
                    body.street,
                    body.postcode,
                    body.city,
                    body.country,
                    user["id"],
                    body.seats,
                ),
            ).fetchone()["id"]
            con.execute(
                "INSERT INTO school_seats (school_id, user_id) VALUES (?, ?)",
                (school_id, user["id"]),
            )
            new_invoice(con, school_id, body.seats)
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Du bist schon an einer Schule.") from None
    school = school_of(con, user["id"])
    assert school is not None
    return teacher_view(con, school, user)


@router.get("/school")
def mine(user: User, con: Con) -> dict:
    school = school_of(con, user["id"])
    if not school:
        raise HTTPException(404)
    return teacher_view(con, school, user)


@router.post("/school/invites")
def invite(body: Invite, user: User, con: Con) -> dict:
    with locked(con):
        school = head_school(con, user)
        running(con, school["year_ends"])
        not_invited(con, school["id"], body.email)
        reserve(con, school["id"], school["seats"])
        token = secrets.token_urlsafe(32)
        con.execute(
            "INSERT INTO school_invites (token, school_id, email) VALUES (?, ?, ?)",
            (auth.digest(token), school["id"], body.email),
        )
    return {"token": token}


@router.post("/school/invites/revoke")
def revoke(body: Invite, user: User, con: Con) -> dict:
    school = head_school(con, user)
    cur = con.execute(
        "DELETE FROM school_invites WHERE school_id = ? AND email = ?", (school["id"], body.email)
    )
    if not cur.rowcount:
        raise HTTPException(404)
    return {}


@router.delete("/school/members/{user_id}")
def remove(user_id: Id, user: User, con: Con) -> dict:
    school = head_school(con, user)
    if user_id == user["id"]:
        raise HTTPException(409, "Die Schulleitung bleibt.")
    cur = con.execute(
        "DELETE FROM school_seats WHERE school_id = ? AND user_id = ?", (school["id"], user_id)
    )
    if not cur.rowcount:
        raise HTTPException(404)
    return {}


@router.get("/school/invites/{token}")
def preview(token: str, con: Con) -> dict:
    row = fresh(con, token)
    if not row:
        raise HTTPException(404)
    return {"email": row["email"], "school": row["name"]}


def take(con: sqlite3.Connection, token: str, email: str) -> sqlite3.Row:
    row = fresh(con, token)
    if not row:
        raise HTTPException(404)
    if row["email"] != email:
        raise HTTPException(409, "Diese Einladung gilt für eine andere E-Mail.")
    running(con, row["year_ends"])
    seat_free(con, row["school_id"], row["seats"])
    return row


@router.post("/school/signup")
def school_signup(body: SchoolSignup, response: Response, con: Con) -> dict:
    with locked(con):
        row = take(con, body.token, body.email)
        try:
            user_id = con.execute(
                "INSERT INTO users (email, password) VALUES (?, ?)",
                (body.email, auth.hasher.hash(body.password)),
            ).lastrowid
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Für diese E-Mail gibt es schon ein Konto.") from None
        assert user_id is not None
        place(con, row["school_id"], user_id, body.token)
    return auth.start_session(con, response, user_id)


@router.post("/school/accept")
def accept(body: Accept, user: User, con: Con) -> dict:
    with locked(con):
        row = take(con, body.token, user["email"])
        not_seated(con, user["id"])
        place(con, row["school_id"], user["id"], body.token)
    school = school_of(con, user["id"])
    assert school is not None
    return teacher_view(con, school, user)


def send_invoice(con: sqlite3.Connection, user: sqlite3.Row, invoice_id: int) -> Response:
    row = con.execute(
        "SELECT invoices.*, schools.name, schools.street, schools.postcode, schools.city,"
        " schools.country, schools.admin_id FROM invoices"
        " JOIN schools ON schools.id = invoices.school_id WHERE invoices.id = ?",
        (invoice_id,),
    ).fetchone()
    if not row or (not user["admin"] and row["admin_id"] != user["id"]):
        raise HTTPException(404)
    if row["status"] == "draft":
        raise HTTPException(409, "Die Rechnung ist noch nicht ausgestellt.")
    filename = f"Rechnung-{row['number']}.pdf"
    return Response(
        pdf(invoice_lines(row)),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/school/invoices/{invoice_id}")
def school_invoice(invoice_id: Id, user: User, con: Con) -> Response:
    return send_invoice(con, user, invoice_id)


@router.get("/admin/invoices/{invoice_id}")
def admin_invoice(invoice_id: Id, admin: Admin, con: Con) -> Response:
    return send_invoice(con, admin, invoice_id)


@router.get("/school/avv")
def avv(user: User, con: Con) -> Response:
    head_school(con, user)
    path = avv_path()
    if path is None:
        raise HTTPException(404, "Der AVV liegt noch nicht vor.")
    return Response(
        path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="AVV.pdf"'},
    )


@router.get("/admin/schools")
def schools(admin: Admin, con: Con) -> list[dict]:
    rows = con.execute("SELECT id FROM schools ORDER BY id")
    return [admin_view(con, row["id"]) for row in rows]


@router.post("/admin/invoices/{invoice_id}")
def issue(invoice_id: Id, body: Issued, admin: Admin, con: Con) -> dict:
    row = con.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    if not row:
        raise HTTPException(404)
    if row["status"] != "draft":
        raise HTTPException(409, "Die Rechnung ist schon ausgestellt.")
    con.execute(
        "UPDATE invoices SET amount_cents = ?, vat_rate = ?, vat_note = ?, tax_number = ?,"
        " seller_address = ?, due = ?, status = 'issued', issued = CURRENT_TIMESTAMP WHERE id = ?",
        (
            body.amount_cents,
            body.vat_rate,
            body.vat_note,
            body.tax_number,
            body.seller_address,
            body.due,
            invoice_id,
        ),
    )
    return admin_view(con, row["school_id"])


@router.post("/admin/invoices/{invoice_id}/paid")
def paid(invoice_id: Id, admin: Admin, con: Con) -> dict:
    row = con.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    if not row:
        raise HTTPException(404)
    if row["status"] == "draft":
        raise HTTPException(409, "Die Rechnung ist noch nicht ausgestellt.")
    if row["status"] == "paid":
        raise HTTPException(409, "Die Rechnung ist schon bezahlt.")
    with locked(con):
        con.execute(
            "UPDATE invoices SET status = 'paid', paid = CURRENT_TIMESTAMP WHERE id = ?",
            (invoice_id,),
        )
        # A date Pascal already set stays. Only a school with no date gets a year from today.
        con.execute(
            "UPDATE schools SET year_ends = coalesce(year_ends, date('now', '+1 year'))"
            " WHERE id = ?",
            (row["school_id"],),
        )
    return admin_view(con, row["school_id"])


@router.post("/admin/schools/{school_id}/year")
def set_year(school_id: Id, body: Year, admin: Admin, con: Con) -> dict:
    if not con.execute("SELECT 1 FROM schools WHERE id = ?", (school_id,)).fetchone():
        raise HTTPException(404)
    con.execute("UPDATE schools SET year_ends = ? WHERE id = ?", (body.year_ends, school_id))
    return admin_view(con, school_id)


@router.post("/admin/schools/{school_id}/invoices")
def another(school_id: Id, admin: Admin, con: Con) -> dict:
    school = con.execute("SELECT * FROM schools WHERE id = ?", (school_id,)).fetchone()
    if not school:
        raise HTTPException(404)
    with locked(con):
        open_row = con.execute(
            "SELECT 1 FROM invoices WHERE school_id = ? AND status != 'paid'", (school_id,)
        ).fetchone()
        if open_row:
            raise HTTPException(409, "Es gibt schon eine offene Rechnung.")
        made = new_invoice(con, school_id, school["seats"])
    return made
