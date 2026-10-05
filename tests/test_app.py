import json

import pytest
from fastapi.testclient import TestClient

from blattwerk import app as appmod


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "TOKEN", "secret")
    monkeypatch.setattr(appmod, "DATA_DIR", tmp_path)
    return TestClient(appmod.app)


def test_form_needs_the_token(client):
    assert client.get("/i/secret").status_code == 200
    assert client.get("/i/wrong").status_code == 404
    assert client.post("/i/wrong", data={"a": "b"}).status_code == 404


def test_empty_token_opens_nothing(client, monkeypatch):
    monkeypatch.setattr(appmod, "TOKEN", "")
    assert client.get("/i/secret").status_code == 404


def test_submit_saves_answers_and_audio(client, tmp_path):
    res = client.post(
        "/i/secret",
        data={"nervt": "Alles langsam", "gut": "Bilder"},
        files=[
            ("audio", ("clip", b"one", "audio/webm;codecs=opus")),
            ("audio", ("clip", b"two", "audio/mp4")),
        ],
    )
    assert res.status_code == 200
    out = tmp_path / res.json()["saved"]
    assert json.loads((out / "answers.json").read_text()) == {
        "nervt": "Alles langsam",
        "gut": "Bilder",
    }
    assert (out / "audio-1.webm").read_bytes() == b"one"
    assert (out / "audio-2.m4a").read_bytes() == b"two"
