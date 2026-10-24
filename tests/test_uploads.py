import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from blattwerk import auth, db, svg
from blattwerk.app import app
from blattwerk.uploads import MAX_BYTES, MAX_SVG_BYTES

PASSWORD = "richtig-geheim"
PNG = b"\x89PNG\r\n\x1a\n not really a picture"


def user(email):
    """A client logged in as a new user. https, or the Secure cookie is not sent back."""
    client = TestClient(app, base_url="https://testserver")
    body = {"token": auth.new_link(db.open_db()), "email": email, "password": PASSWORD}
    assert client.post("/api/signup", json=body).status_code == 200
    return client


def send(client, data=PNG, kind="image/png"):
    return client.post("/api/uploads", files={"file": ("bild", data, kind)})


def test_logged_out_gets_401():
    client = TestClient(app, base_url="https://testserver")
    assert send(client).status_code == 401
    assert client.get("/api/uploads/1").status_code == 401


def test_upload_comes_back_as_sent(data_dir):
    client = user("a@example.com")
    upload_id = send(client).json()["id"]
    res = client.get(f"/api/uploads/{upload_id}")
    assert res.content == PNG
    assert res.headers["content-type"] == "image/png"
    assert (data_dir / "users" / "1" / "uploads" / str(upload_id)).read_bytes() == PNG
    assert client.get("/api/uploads/99").status_code == 404


def test_uploads_belong_to_one_user():
    client = user("a@example.com")
    other = user("b@example.com")
    upload_id = send(client).json()["id"]
    assert other.get(f"/api/uploads/{upload_id}").status_code == 404
    # An upload of their own does not open the first user's either.
    assert send(other).json()["id"] != upload_id
    assert other.get(f"/api/uploads/{upload_id}").status_code == 404
    assert client.get(f"/api/uploads/{upload_id}").status_code == 200


def test_only_pictures_of_a_sane_size():
    client = user("a@example.com")
    # This SVG has no size to give it, so it is refused, onload or not. Cleaning is tested below.
    assert send(client, b"<svg onload='alert(1)'/>", "image/svg+xml").status_code == 415
    assert send(client, b"%PDF", "application/pdf").status_code == 415
    assert send(client, b"x" * (MAX_BYTES + 1)).status_code == 413
    assert db.open_db().execute("SELECT count(*) FROM uploads").fetchone()[0] == 0


SVG_NS = 'xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"'
SVG_OPEN = f'<svg {SVG_NS} viewBox="0 0 10 10">'
CLEAN_SVG = f'{SVG_OPEN}<rect width="5" height="5"/></svg>'.encode()


def svg_of(inner, root_attrs='viewBox="0 0 10 10"'):
    """An SVG with a size and a shape that must survive the cleaning."""
    kept = '<rect id="kept" width="5" height="5"/>'
    return f"<svg {SVG_NS} {root_attrs}>{inner}{kept}</svg>".encode()


# Each hostile part, the words that must be gone from the served bytes afterwards.
HOSTILE = {
    "script": (svg_of("<script>alert(1)</script>"), [b"script", b"alert"]),
    "onload": (svg_of("", 'viewBox="0 0 10 10" onload="alert(1)"'), [b"onload", b"alert"]),
    "onclick": (svg_of('<circle r="1" onclick="alert(1)"/>'), [b"onclick", b"alert"]),
    "a-href": (svg_of('<a href="http://x"><circle r="1"/></a>'), [b"http://x", b"<a"]),
    "use-href": (svg_of('<use href="http://evil/x.svg#a"/>'), [b"evil"]),
    "use-xlink-href": (svg_of('<use xlink:href="http://evil"/>'), [b"evil"]),
    "fill-url": (svg_of('<circle r="1" fill="url(http://evil/x)"/>'), [b"evil"]),
    "style-url": (svg_of('<circle r="1" style="fill:url(https://evil)"/>'), [b"evil"]),
    "style-import": (svg_of("<style>@import url(http://evil);</style>"), [b"evil", b"@import"]),
    "foreignObject": (
        svg_of(
            '<foreignObject><body xmlns="http://www.w3.org/1999/xhtml">'
            '<img src="x" onerror="alert(1)"/></body></foreignObject>'
        ),
        [b"foreignObject", b"onerror", b"alert"],
    ),
    "javascript-href": (svg_of('<use href="javascript:alert(1)"/>'), [b"javascript", b"alert"]),
    "set": (
        svg_of('<set attributeName="href" to="javascript:alert(1)"/>'),
        [b"<set", b"javascript"],
    ),
    "style-child": (
        svg_of(
            "<style><title/>@import url(http://evil/a.css); rect{fill:url(http://evil/x)}</style>"
        ),
        [b"evil", b"@import", b"<title"],
    ),
    "image-set": (svg_of("""<rect fill='image-set("http://evil/z.png" 1x)'/>"""), [b"evil"]),
    "webkit-image-set": (
        svg_of("""<rect style='fill:-webkit-image-set("http://evil/z.png" 1x)'/>"""),
        [b"evil", b"image-set"],
    ),
    "other-namespace": (
        svg_of('<x:foo xmlns:x="http://evil.example/ns"><circle r="1"/></x:foo>'),
        [b"evil", b"foo"],
    ),
}


@pytest.mark.parametrize("data, gone", list(HOSTILE.values()), ids=list(HOSTILE))
def test_hostile_svg_is_cleaned_before_it_is_stored(data, gone):
    client = user("a@example.com")
    upload_id = send(client, data, "image/svg+xml").json()["id"]
    res = client.get(f"/api/uploads/{upload_id}")
    assert res.status_code == 200
    assert b'id="kept"' in res.content
    for word in gone:
        assert word not in res.content


# Each one is refused before it is read, so each starts with a head that makes it look like SVG.
REFUSED_SVG = {
    "internal-entity": (
        f'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY e "x">]>{SVG_OPEN}<text>&e;</text></svg>'
    ),
    "external-entity": (
        f'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY e SYSTEM "file:///etc/passwd">]>'
        f"{SVG_OPEN}<text>&e;</text></svg>"
    ),
    "billion-laughs": (
        '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
        '<!ENTITY lol2 "&lol;&lol;&lol;&lol;"><!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;">]>'
        f"{SVG_OPEN}<text>&lol3;</text></svg>"
    ),
    "doctype-with-subset": (
        '<?xml version="1.0"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
        '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd" [<!ELEMENT svg ANY>]>'
        f"{SVG_OPEN}</svg>"
    ),
    "xml-stylesheet": (
        '<?xml version="1.0"?><?xml-stylesheet href="http://evil/x.css" type="text/css"?>'
        f"{SVG_OPEN}</svg>"
    ),
}


@pytest.mark.parametrize("data", list(REFUSED_SVG.values()), ids=list(REFUSED_SVG))
def test_svg_with_entities_or_doctype_is_refused(data_dir, data):
    client = user("a@example.com")
    assert send(client, data.encode(), "image/svg+xml").status_code == 415
    assert db.open_db().execute("SELECT count(*) FROM uploads").fetchone()[0] == 0
    assert not list(data_dir.glob("users/*/uploads/*"))


NOT_SVG = {
    "broken-xml": f'<?xml version="1.0"?><svg {SVG_NS}><rect></svg>',
    "html-root": '<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><body/></html>',
    "no-namespace": '<svg viewBox="0 0 10 10"><rect width="1" height="1"/></svg>',
    "no-size": f'<svg {SVG_NS}><rect width="1" height="1"/></svg>',
}


@pytest.mark.parametrize("data", list(NOT_SVG.values()), ids=list(NOT_SVG))
def test_svg_that_is_not_svg_is_refused(data_dir, data):
    client = user("a@example.com")
    assert send(client, data.encode(), "image/svg+xml").status_code == 415
    assert db.open_db().execute("SELECT count(*) FROM uploads").fetchone()[0] == 0
    assert not list(data_dir.glob("users/*/uploads/*"))


def test_svg_gets_width_height_and_viewbox():
    client = user("a@example.com")
    only_box = f'<svg {SVG_NS} viewBox="0 0 30 20"><rect width="1" height="1"/></svg>'
    only_size = f'<svg {SVG_NS} width="40px" height="25"><rect width="1" height="1"/></svg>'
    grad = (
        f'{SVG_OPEN}<defs><linearGradient id="grad"/></defs>'
        '<rect width="5" height="5" fill="url(#grad)"/></svg>'
    )

    def served(data):
        upload_id = send(client, data.encode(), "image/svg+xml").json()["id"]
        return client.get(f"/api/uploads/{upload_id}").content

    root = ET.fromstring(served(only_box))
    assert (root.get("width"), root.get("height")) == ("30", "20")
    root = ET.fromstring(served(only_size))
    assert (root.get("width"), root.get("height")) == ("40", "25")
    assert root.get("viewBox") == "0 0 40 25"
    assert b'fill="url(#grad)"' in served(grad)


def test_svg_answer_carries_csp_and_nosniff():
    client = user("a@example.com")
    svg_id = send(client, CLEAN_SVG, "image/svg+xml").json()["id"]
    res = client.get(f"/api/uploads/{svg_id}")
    assert res.headers["content-security-policy"] == (
        "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    )
    assert res.headers["x-content-type-options"] == "nosniff"
    png_id = send(client).json()["id"]
    res = client.get(f"/api/uploads/{png_id}")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert "content-security-policy" not in res.headers


def test_svg_is_stored_as_svg(data_dir):
    client = user("a@example.com")
    upload_id = send(client, CLEAN_SVG, "image/svg+xml").json()["id"]
    res = client.get(f"/api/uploads/{upload_id}")
    assert res.headers["content-type"] == "image/svg+xml"
    assert res.content.startswith(b"<svg")
    assert (data_dir / "users" / "1" / "uploads" / str(upload_id)).is_file()


ILLUSTRATOR = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
    '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'
    f'{SVG_OPEN}<rect id="kept" width="5" height="5"/></svg>'
).encode()


def test_illustrator_doctype_is_taken_and_stored_without_it():
    client = user("a@example.com")
    upload_id = send(client, ILLUSTRATOR, "image/svg+xml").json()["id"]
    res = client.get(f"/api/uploads/{upload_id}")
    assert b'id="kept"' in res.content
    assert b"DOCTYPE" not in res.content


def test_svg_after_a_comment_is_taken():
    client = user("a@example.com")
    data = f"<!-- made by x -->\n{CLEAN_SVG.decode()}".encode()
    upload_id = send(client, data, "image/svg+xml").json()["id"]
    res = client.get(f"/api/uploads/{upload_id}")
    assert res.status_code == 200
    assert res.content.startswith(b"<svg")
    assert b"made by x" not in res.content


def test_svg_size_is_written_as_plain_decimals():
    client = user("a@example.com")
    exponent = f'<svg {SVG_NS} width="2e2" height="+1e2"><rect width="1" height="1"/></svg>'
    from_box = f'<svg {SVG_NS} viewBox="0 0 2.50 1e1"><rect width="1" height="1"/></svg>'

    def served(data):
        upload_id = send(client, data.encode(), "image/svg+xml").json()["id"]
        return ET.fromstring(client.get(f"/api/uploads/{upload_id}").content)

    root = served(exponent)
    assert (root.get("width"), root.get("height")) == ("200", "100")
    root = served(from_box)
    assert (root.get("width"), root.get("height")) == ("2.5", "10")


def test_svg_over_its_own_limit_is_refused_before_cleaning(data_dir):
    client = user("a@example.com")
    # Trailing spaces after the root keep it SVG and make it too big.
    big = CLEAN_SVG + b" " * MAX_SVG_BYTES
    assert send(client, big, "image/svg+xml").status_code == 413
    assert db.open_db().execute("SELECT count(*) FROM uploads").fetchone()[0] == 0
    assert not list(data_dir.glob("users/*/uploads/*"))


def test_cleaned_svg_over_the_picture_limit_is_refused(monkeypatch):
    # Cleaning only shrinks an SVG in practice, so this stands in for a cleaned file that grew.
    monkeypatch.setattr(svg, "clean", lambda data: b"x" * (MAX_BYTES + 1))
    client = user("a@example.com")
    assert send(client, CLEAN_SVG, "image/svg+xml").status_code == 413
    assert db.open_db().execute("SELECT count(*) FROM uploads").fetchone()[0] == 0


TEXT = b"Kein Bild, nur Text.\n"
# One picture of each kind the browser draws: the first bytes say which.
PICTURES = {
    "image/jpeg": b"\xff\xd8\xff\xe0 not really a picture",
    "image/png": PNG,
    "image/webp": b"RIFF\x24\x00\x00\x00WEBPVP8 not really a picture",
    "image/gif": b"GIF89a not really a picture",
}


@pytest.mark.parametrize("declared", [*PICTURES, "text/plain"])
def test_bytes_that_are_no_picture_are_refused_whatever_the_type(data_dir, declared):
    """18: text sent as a picture of any declared type is refused, and nothing is kept."""
    client = user("a@example.com")
    assert send(client, TEXT, declared).status_code == 415
    assert db.open_db().execute("SELECT count(*) FROM uploads").fetchone()[0] == 0
    assert not list(data_dir.glob("users/*/uploads/*"))


def test_an_empty_file_is_refused(data_dir):
    """18"""
    client = user("a@example.com")
    assert send(client, b"", "image/png").status_code == 415
    assert db.open_db().execute("SELECT count(*) FROM uploads").fetchone()[0] == 0


@pytest.mark.parametrize("kind", list(PICTURES))
def test_a_picture_is_stored_as_its_bytes_show_whatever_type_is_declared(kind):
    """19: the stored and served type is the one the bytes show."""
    client = user("a@example.com")
    for declared in [*PICTURES, "text/plain"]:
        upload_id = send(client, PICTURES[kind], declared).json()["id"]
        res = client.get(f"/api/uploads/{upload_id}")
        assert res.content == PICTURES[kind]
        assert res.headers["content-type"] == kind


def test_delete_account_removes_uploads(data_dir):
    client = user("a@example.com")
    other = user("b@example.com")
    send(client)
    kept = send(other).json()["id"]
    assert client.delete("/api/me").status_code == 200
    assert not (data_dir / "users" / "1").exists()
    assert [r["user_id"] for r in db.open_db().execute("SELECT user_id FROM uploads")] == [2]
    assert other.get(f"/api/uploads/{kept}").content == PNG
