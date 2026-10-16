import re

from fastapi.testclient import TestClient

from blattwerk.app import app


def test_privacy_page_names_claude_desktop_and_its_recipient():
    text = TestClient(app).get("/datenschutz").text
    for word in ("Anthropic", "Claude Desktop", "Lernwörter"):
        assert word in text
    assert "Widerrufen" in text or "widerrufen" in text


def test_privacy_sections_run_in_order():
    text = TestClient(app).get("/datenschutz").text
    numbers = [int(n) for n in re.findall(r"<h2>(\d+)\. ", text)]
    assert numbers == list(range(1, 12))
