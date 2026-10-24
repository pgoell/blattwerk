"""Public pages, the maths list, the command line and which browser a test gets."""

import os
import subprocess
import sys

from fastapi.testclient import TestClient
from test_app import (
    MATHS,
    user,
)
from ui import BROWSER

from blattwerk.app import app


def test_maths_exercises():
    client = user("a@example.com")
    out = client.post("/api/maths", json=MATHS).json()
    assert len(out["exercises"]) == 3
    assert out["loosen"] is None
    assert client.post("/api/maths", json={**MATHS, "max": 0}).status_code == 422


def test_legal_pages_are_public():
    client = TestClient(app)
    assert "Impressum" in client.get("/impressum").text
    assert "Datenschutzerklärung" in client.get("/datenschutz").text


def test_legal_pages_say_blattomat():
    client = TestClient(app)
    for path in ("/impressum", "/datenschutz"):
        res = client.get(path)
        assert res.status_code == 200
        title, body = res.text.split("</title>")
        assert "Blattomat" in title and "Blattomat" in body
        # The old name is gone, however it was written.
        assert "blattwerk" not in res.text.lower()


def test_cli_help_says_blattomat(tmp_path):
    # No word after the command: it prints its help and fails. The command keeps its name.
    env = {**os.environ, "BLATTWERK_DATA_DIR": str(tmp_path)}
    res = subprocess.run(
        [sys.executable, "-m", "blattwerk"], capture_output=True, text=True, env=env
    )
    assert res.returncode != 0
    assert "Blattomat" in res.stderr
    assert "python -m blattwerk invite" in res.stderr


def test_the_browser_is_the_one_asked_for(editor):
    agent = editor().evaluate("navigator.userAgent")
    # Chromium names AppleWebKit too, so only the word Chrome tells the two apart.
    assert "AppleWebKit" in agent
    assert ("Chrome" not in agent) == (BROWSER == "webkit")


def test_a_touch_test_runs_as_an_ipad(editor):
    page = editor(touch=True)
    assert page.evaluate("'ontouchstart' in window")
    assert ("iPad" in page.evaluate("navigator.userAgent")) == (BROWSER == "webkit")
