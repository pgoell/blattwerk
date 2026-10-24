"""The teacher the stage signs up: what that account can see, and a sign-in over plain http.

The helpers live in test_stage.py.
"""

import os
import subprocess
import sys
from http.cookies import SimpleCookie
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import expect
from test_canary import ROOT
from test_stage import (
    EMAIL,
    EMAIL_2,
    TEACHER,
)
from ui import BROWSER, PASSWORD, TEXT, box, sheet, upload, user

from blattwerk import auth, db
from blattwerk.app import app

# ── stage-teacher.py ──


def teacher(server, invite, email):
    """Runs the script as the container would: fed on stdin, the invite in the environment."""
    env = {**os.environ, "STAGE_INVITE": invite}
    with TEACHER.open() as script:
        return subprocess.run(
            [sys.executable, "-", server, email],
            stdin=script,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )


def test_a6_the_teacher_sees_nothing_of_another_account(server):
    other = user()
    theirs = sheet(other, [box("a", "text", TEXT)])
    kept = other.post("/api/templates", json={"name": "Meine", "doc": theirs["doc"]}).json()
    picture = upload(other)
    invite = "/einladung/" + auth.new_link(db.open_db())
    done = teacher(server, invite, EMAIL)
    assert done.returncode == 0, done.stderr
    first, second = done.stdout.splitlines()
    assert first == f"E-Mail: {EMAIL}"
    password = second.removeprefix("Passwort: ")
    assert invite.rsplit("/", 1)[1] not in done.stdout + done.stderr

    # The printed login, over http as the session on the stage uses it.
    login = httpx.post(f"{server}/api/login", json={"email": EMAIL, "password": password})
    assert login.status_code == 200
    assert login.json()["admin"] is False
    session = SimpleCookie(login.headers["set-cookie"])["session"].value

    def get(path):
        return httpx.get(f"{server}{path}", headers={"Cookie": f"session={session}"})

    assert get("/api/sheets").json() == []
    # The built-in templates are everyone's: their ids lie below zero.
    assert kept["id"] > 0
    assert all(template["id"] < 0 for template in get("/api/templates").json())
    assert get(f"/api/sheets/{theirs['id']}").status_code == 404
    assert get(f"/api/sheets/{theirs['id']}/pdf").status_code == 404
    assert get(f"/api/uploads/{picture}").status_code == 404
    # The admin's list is as missing as it is for every teacher.
    assert get("/api/admin/users").status_code == 404
    # And the other account still has what it had.
    assert [found["id"] for found in other.get("/api/sheets").json()] == [theirs["id"]]


def test_a6_the_second_teacher_sees_nothing_of_the_first(server):
    first_invite = "/einladung/" + auth.new_link(db.open_db())
    second_invite = "/einladung/" + auth.new_link(db.open_db())
    done = teacher(server, first_invite, EMAIL)
    assert done.returncode == 0, done.stderr
    first_password = done.stdout.splitlines()[1].removeprefix("Passwort: ")
    done = teacher(server, second_invite, EMAIL_2)
    assert done.returncode == 0, done.stderr
    second_password = done.stdout.splitlines()[1].removeprefix("Passwort: ")

    def session_of(email, password):
        login = httpx.post(f"{server}/api/login", json={"email": email, "password": password})
        assert login.status_code == 200
        return SimpleCookie(login.headers["set-cookie"])["session"].value

    def get(session, path):
        return httpx.get(f"{server}{path}", headers={"Cookie": f"session={session}"})

    # The first teacher makes a sheet, a template and a picture, as the app does for a teacher.
    first = TestClient(app, base_url="https://testserver")
    assert first.post("/api/login", json={"email": EMAIL, "password": first_password}).is_success
    doc = {"pages": [{"blocks": []}], "guides": {"x": [], "y": []}, "grid": 0}
    made = first.post("/api/sheets", json={"title": "Erstes", "doc": doc}).json()
    kept = first.post("/api/templates", json={"name": "Meine", "doc": doc}).json()
    picture = upload(first)

    second = session_of(EMAIL_2, second_password)
    assert get(second, "/api/sheets").json() == []
    assert get(second, f"/api/sheets/{made['id']}").status_code == 404
    assert kept["id"] > 0
    assert all(template["id"] < 0 for template in get(second, "/api/templates").json())
    assert (
        httpx.delete(
            f"{server}/api/templates/{kept['id']}", headers={"Cookie": f"session={second}"}
        ).status_code
        == 404
    )
    assert get(second, f"/api/uploads/{picture}").status_code == 404
    # And the first teacher still has what was theirs.
    assert [found["id"] for found in first.get("/api/sheets").json()] == [made["id"]]


def test_a5_a_dead_invite_makes_no_teacher_and_prints_no_login(server):
    done = teacher(server, "/einladung/nothing", EMAIL)
    assert done.returncode == 1
    assert done.stdout == ""
    assert done.stderr == "stage teacher failed: /api/signup: status 404\n"
    assert db.open_db().execute("SELECT count(*) FROM users").fetchone()[0] == 0


# ── the browser on the stage's address ──


@pytest.mark.skipif(BROWSER == "webkit", reason="WebKit keeps no Secure cookie from plain http")
def test_i1_a_browser_signs_in_on_plain_http_and_stays_signed_in(browser, server):
    email = f"{uuid4().hex}@example.com"
    user(email)
    # A new context with no cookie put in by hand: the form alone signs in, as on the stage.
    context = browser.new_context()
    try:
        page = context.new_page()
        page.goto(server)
        page.locator("#email").click()
        page.keyboard.type(email)
        page.locator("#password").click()
        page.keyboard.type(PASSWORD)
        page.keyboard.press("Enter")
        home = page.get_by_role("heading", name="Meine Blätter")
        expect(home).to_be_visible()
        (cookie,) = [c for c in context.cookies() if c["name"] == "session"]
        assert cookie["secure"]
        page.reload()
        expect(home).to_be_visible()
        expect(page.locator("#email")).to_have_count(0)
    finally:
        context.close()


# ── the docs ──


def test_i7_the_readme_names_both_tasks():
    readme = (ROOT / "README.md").read_text()
    assert "mise run stage:up" in readme
    assert "mise run stage:down" in readme
