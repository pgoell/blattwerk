import re

from fastapi.testclient import TestClient

from blattwerk.app import app


def test_privacy_page_names_claude_desktop_and_its_recipient():
    text = TestClient(app).get("/datenschutz").text
    section = re.split(r"<h2[^>]*>9\. ", text, maxsplit=1)[1].split("<h2>10. ", 1)[0]
    for word in ("Anthropic", "Claude Desktop", "Lernwörter", "entfernen", "widerrufen"):
        assert word in section


def test_privacy_sections_run_in_order():
    text = TestClient(app).get("/datenschutz").text
    numbers = [int(n) for n in re.findall(r"<h2[^>]*>(\d+)\. ", text)]
    assert numbers == list(range(1, 13))


def test_privacy_names_pixabay_and_keeps_the_teacher_off_the_search():
    """The search term goes to Pixabay. The teacher's name and mail do not. Openclipart is not asked."""
    text = TestClient(app).get("/datenschutz").text
    assert "<h2>12. Bildsuche</h2>" in text
    section = text.split("<h2>12. Bildsuche</h2>", 1)[1].split('<p><a href="/impressum">', 1)[0]
    for word in ("Pixabay", "Canva Germany GmbH", "Suchbegriff", "Openclipart"):
        assert word in section
    assert "nicht Ihre E-Mail-Adresse" in section
    assert "nicht Ihr Name" in section
