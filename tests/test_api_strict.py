from test_tokens import bearer, make
from ui import block, maths, sheet, user

MATHS_PROPS = {"ops": ["+"], "max": 20, "count": 3, "seed": 7}


def maths_doc(client, columns=3):
    """A sheet's doc with one maths block, as the editor makes it, with `columns` columns."""
    props = maths(client, columns=columns)
    return {
        "pages": [{"blocks": [block("maths", 20, 40, props)]}],
        "guides": {"x": [], "y": []},
        "grid": 0,
    }


def test_token_reaches_maths_and_templates():
    client = user()
    api = bearer(make(client))
    assert api.post("/api/maths", json=MATHS_PROPS).status_code == 200
    assert api.get("/api/templates").status_code == 200


def test_revoked_token_gets_401_on_maths():
    client = user()
    token = make(client)
    token_id = client.get("/api/tokens").json()[0]["id"]
    assert client.delete(f"/api/tokens/{token_id}").status_code == 200
    assert bearer(token).post("/api/maths", json=MATHS_PROPS).status_code == 401


def test_strict_patch_refuses_a_fault_that_plain_patch_saves():
    client = user()
    made = sheet(client, [block("maths", 20, 40, maths(client))])
    wrong = maths_doc(client, columns=7)

    plain = client.patch(
        f"/api/sheets/{made['id']}", json={"doc": wrong, "version": made["version"]}
    )
    assert plain.status_code == 200
    stored = client.get(f"/api/sheets/{made['id']}").json()

    strict = client.patch(
        f"/api/sheets/{made['id']}?strict=true",
        json={"doc": maths_doc(client, columns=7), "version": plain.json()["version"]},
    )
    assert strict.status_code == 422
    problems = strict.json()["detail"]["problems"]
    assert any("pages[0].blocks[0].props.columns" in p and "must be 1 to" in p for p in problems)
    assert client.get(f"/api/sheets/{made['id']}").json()["doc"] == stored["doc"]


def test_strict_patch_with_stale_version_is_409_for_a_sound_doc():
    client = user()
    made = sheet(client, [block("maths", 20, 40, maths(client))])
    body = {"doc": maths_doc(client), "version": made["version"] + 5}
    assert client.patch(f"/api/sheets/{made['id']}?strict=true", json=body).status_code == 409


def test_strict_post_saves_a_sound_doc():
    client = user()
    body = {"title": "Plus", "doc": maths_doc(client)}
    assert client.post("/api/sheets?strict=true", json=body).status_code == 200


def test_strict_post_refuses_a_fault_that_plain_post_saves():
    client = user()
    doc = maths_doc(client)
    text = {"text": "Hallo", "size": "gross", "align": "left"}
    doc["pages"] = [{"blocks": [block("text", 20, 20, text)]}]
    body = {"title": "Text", "doc": doc}
    assert client.post("/api/sheets", json=body).status_code == 200
    res = client.post("/api/sheets?strict=true", json=body)
    assert res.status_code == 422
    assert any("pages[0].blocks[0].props.size" in p for p in res.json()["detail"]["problems"])
