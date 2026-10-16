import logging
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from ui import sheet, upload, user

from blattwerk import auth, db
from blattwerk.app import app

PASSWORD = "richtig-geheim"
PNG = b"\x89PNG\r\n\x1a\n x"


def make(client, name="Claude Desktop"):
    res = client.post("/api/tokens", json={"name": name})
    assert res.status_code == 200
    return res.json()["token"]


def bearer(token):
    return TestClient(
        app, base_url="https://testserver", headers={"Authorization": f"Bearer {token}"}
    )


def listed(client):
    return {t["name"]: t for t in client.get("/api/tokens").json()}


def admin_user():
    client = TestClient(app, base_url="https://testserver")
    body = {
        "token": auth.new_link(db.open_db(), admin=True),
        "email": f"{uuid4().hex}@example.com",
        "password": PASSWORD,
    }
    assert client.post("/api/signup", json=body).status_code == 200
    return client


def test_token_does_the_teacher_work():
    client = user()
    token = make(client)
    rows = client.get("/api/tokens").json()
    assert len(rows) == 1
    assert set(rows[0]) == {"id", "name", "created", "last_used"}
    assert rows[0]["name"] == "Claude Desktop"
    assert rows[0]["last_used"] is None

    api = bearer(token)
    made = sheet(api, title="Plus")
    saved = {"title": "Minus", "doc": made["doc"], "version": made["version"]}
    assert api.patch(f"/api/sheets/{made['id']}", json=saved).status_code == 200
    # The same version again is stale now.
    assert api.patch(f"/api/sheets/{made['id']}", json=saved).status_code == 409
    assert [s["id"] for s in api.get("/api/sheets").json()] == [made["id"]]
    assert api.post(f"/api/sheets/{made['id']}/duplicate").status_code == 200
    assert api.delete(f"/api/sheets/{made['id']}").status_code == 200

    client.delete(f"/api/tokens/{rows[0]['id']}")
    assert api.get("/api/sheets").status_code == 401


def test_list_has_no_token_and_no_hash():
    client = user()
    token = make(client)
    for row in client.get("/api/tokens").json():
        assert "token" not in row and "hash" not in row
        assert token not in str(row)


def test_only_the_hash_is_stored(data_dir):
    client = user()
    token = make(client)
    con = db.open_db()
    stored = con.execute("SELECT hash FROM tokens").fetchone()["hash"]
    assert stored != token
    files = b"".join(p.read_bytes() for p in data_dir.glob("blattwerk.db*"))
    assert token.encode() not in files


def test_token_uploads_and_fetches_a_picture():
    api = bearer(make(user()))
    upload_id = api.post("/api/uploads", files={"file": ("bild", PNG, "image/png")}).json()["id"]
    res = api.get(f"/api/uploads/{upload_id}")
    assert res.status_code == 200
    assert res.content == PNG


def test_other_teacher_token_sees_nothing():
    a = user()
    b = user()
    sheet_id = sheet(a, title="A")["id"]
    upload_id = upload(a)
    other = bearer(make(b))
    assert other.get(f"/api/sheets/{sheet_id}").status_code == 404
    assert other.patch(f"/api/sheets/{sheet_id}", json={"title": "X"}).status_code == 404
    assert other.post(f"/api/sheets/{sheet_id}/duplicate").status_code == 404
    assert other.get(f"/api/sheets/{sheet_id}/variante/B").status_code == 404
    assert other.get(f"/api/sheets/{sheet_id}/pdf").status_code == 404
    assert other.get(f"/api/uploads/{upload_id}").status_code == 404
    assert other.delete(f"/api/sheets/{sheet_id}").status_code == 404
    assert other.get("/api/sheets").json() == []
    assert a.get(f"/api/sheets/{sheet_id}").status_code == 200


def test_admin_token_is_no_admin():
    admin = admin_user()
    api = bearer(make(admin))
    assert api.get("/api/admin/users").status_code == 401
    assert api.post("/api/admin/invites").status_code == 401
    assert api.post("/api/tokens", json={"name": "x"}).status_code == 401
    assert api.get("/api/tokens").status_code == 401
    assert api.delete("/api/me").status_code == 401
    assert admin.get("/api/me").status_code == 200


def test_bad_header_beside_cookie_is_401():
    client = user()
    token = make(client)
    assert (
        client.get("/api/sheets", headers={"Authorization": "Bearer bt_1_nope"}).status_code == 401
    )
    token_id = listed(client)["Claude Desktop"]["id"]
    client.delete(f"/api/tokens/{token_id}")
    revoked = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/sheets", headers=revoked).status_code == 401
    assert client.get("/api/sheets").status_code == 200


def test_account_deleted_kills_the_token():
    client = user()
    api = bearer(make(client))
    assert client.delete("/api/me").status_code == 200
    assert api.get("/api/sheets").status_code == 401


def test_password_reset_kills_the_token():
    client = user()
    api = bearer(make(client))
    user_id = client.get("/api/me").json()["id"]
    link = auth.new_link(db.open_db(), user_id)
    assert (
        client.post("/api/reset", json={"token": link, "password": "neues-geheim"}).status_code
        == 200
    )
    assert api.get("/api/sheets").status_code == 401


def test_bad_tokens_are_rate_limited():
    client = user()
    good = make(client)
    for _ in range(10):
        assert bearer("bt_1_nope").get("/api/sheets").status_code == 401
    assert bearer("bt_1_nope").get("/api/sheets").status_code == 429
    # A school shares one address: the bad tries never block a good token.
    assert bearer(good).get("/api/sheets").status_code == 200


def test_a_revoked_token_from_one_address_blocks_no_good_token_and_no_login():
    client = user("schule@example.com")
    revoked = make(client, "alt")
    client.delete(f"/api/tokens/{listed(client)['alt']['id']}")
    good = make(user(), "gut")
    codes = {bearer(revoked).get("/api/sheets").status_code for _ in range(25)}
    assert codes == {401, 429}
    assert bearer(good).get("/api/sheets").status_code == 200
    fresh = TestClient(app, base_url="https://testserver")
    login = {"email": "schule@example.com", "password": PASSWORD}
    assert fresh.post("/api/login", json=login).status_code == 200
    assert fresh.get("/api/sheets").status_code == 200


def test_malformed_headers_are_401():
    client = user()
    make(client)
    headers = [
        "Basic x",
        "Bearer",
        "Bearer bt_x_y",
        "Bearer bt_99999999999999999999999_y",
        "Bearer bt_1",
    ]
    for header in headers:
        res = client.get("/api/sheets", headers={"Authorization": header})
        assert res.status_code == 401, header


def test_revoke_one_token_keeps_the_other():
    a = user()
    b = user()
    t1 = make(a, "eins")
    t2 = make(a, "zwei")
    tb = make(b, "B")
    a.delete(f"/api/tokens/{listed(a)['eins']['id']}")
    assert bearer(t1).get("/api/sheets").status_code == 401
    assert bearer(t2).get("/api/sheets").status_code == 200
    assert a.delete(f"/api/tokens/{listed(b)['B']['id']}").status_code == 404
    assert bearer(tb).get("/api/sheets").status_code == 200


def test_last_used_is_filled_by_a_bearer_request():
    client = user()
    token = make(client)
    assert listed(client)["Claude Desktop"]["last_used"] is None
    bearer(token).get("/api/sheets")
    assert listed(client)["Claude Desktop"]["last_used"] is not None


def test_name_is_stripped_and_checked():
    client = user()
    for name in ["", "   ", "x" * 81]:
        assert client.post("/api/tokens", json={"name": name}).status_code == 422
    res = client.post("/api/tokens", json={"name": "  Claude  "})
    assert res.json()["name"] == "Claude"
    assert "Claude" in listed(client)


def test_token_is_never_logged(caplog):
    client = user()
    token = make(client)
    with caplog.at_level(logging.DEBUG):
        assert bearer(token).get("/api/sheets").status_code == 200
        assert bearer("bt_1_nope").get("/api/sheets").status_code == 401
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert token not in text
    assert token.split("_", 2)[2] not in text


def test_secret_of_another_token_under_its_id_is_401():
    client = user()
    first = make(client, "eins")
    make(client, "zwei")
    first_id = listed(client)["eins"]["id"]
    second_id = listed(client)["zwei"]["id"]
    forged = f"bt_{second_id}_{first.split('_', 2)[2]}"
    assert bearer(forged).get("/api/sheets").status_code == 401
    assert bearer(first).get("/api/sheets").status_code == 200
    assert first_id != second_id


def test_name_of_eighty_characters_is_kept():
    client = user()
    name = "x" * 80
    assert client.post("/api/tokens", json={"name": f"  {name}  "}).json()["name"] == name


def test_token_prints_and_varies_its_own_sheet(server):
    client = user()
    token = make(client)
    sheet_id = sheet(client, title="Plus")["id"]
    auth_header = {"Authorization": f"Bearer {token}"}
    assert bearer(token).get(f"/api/sheets/{sheet_id}/variante/B").status_code == 200
    res = httpx.get(f"{server}/api/sheets/{sheet_id}/pdf", headers=auth_header, timeout=60)
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF")


def test_cookie_routes_ignore_the_header():
    client = user()
    bad = {"Authorization": "Bearer bt_1_nope"}
    assert client.get("/api/me", headers=bad).status_code == 200
    assert client.post("/api/tokens", json={"name": "x"}, headers=bad).status_code == 200
    assert client.get("/api/tokens", headers=bad).status_code == 200


def test_bad_tries_from_before_the_window_do_not_count():
    good = make(user())
    con = db.open_db()
    for _ in range(10):
        con.execute(
            "INSERT INTO attempts (key, created) VALUES ('token:testclient', '2026-01-01 08:00:00')"
        )
    con.close()
    assert bearer("bt_1_nope").get("/api/sheets").status_code == 401
    assert bearer(good).get("/api/sheets").status_code == 200


def test_a_name_already_used_is_refused_whatever_the_case_and_spaces():
    client = user()
    make(client, "Laptop Schule")
    res = client.post("/api/tokens", json={"name": " laptop schule "})
    assert res.status_code == 422
    assert list(listed(client)) == ["Laptop Schule"]
    make(client, "Äpfel")
    assert client.post("/api/tokens", json={"name": "äpfel"}).status_code == 422


def test_a_name_is_free_again_once_its_key_is_revoked():
    client = user()
    make(client, "Laptop Schule")
    client.delete(f"/api/tokens/{listed(client)['Laptop Schule']['id']}")
    assert client.post("/api/tokens", json={"name": "Laptop Schule"}).status_code == 200


def test_another_teacher_may_use_the_same_name():
    make(user(), "Laptop Schule")
    assert make(user(), "Laptop Schule")


def test_a_name_of_81_characters_is_refused():
    client = user()
    assert client.post("/api/tokens", json={"name": "x" * 81}).status_code == 422
    assert listed(client) == {}


def test_a_blank_name_is_refused():
    client = user()
    assert client.post("/api/tokens", json={"name": "  "}).status_code == 422
