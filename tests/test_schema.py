import copy
import json
from pathlib import Path

from ui import sheet, user

from blattwerk import db, templates
from blattwerk.schema import problems

SCHEMA = Path(__file__).parent.parent / "src/blattwerk/sheet.schema.json"
CORPUS = Path(__file__).parent / "corpus"


def doc(*blocks, **more):
    return {"pages": [{"blocks": list(blocks)}], "guides": {"x": [], "y": []}, "grid": 0, **more}


def text_block(**props):
    base = {"text": "Hallo", "size": 14, "align": "left"}
    return {
        "id": "a",
        "type": "text",
        "x": 15,
        "y": 20,
        "w": 180,
        "h": 10,
        "z": 1,
        "locked": False,
        "props": {**base, **props},
    }


def built_in(name):
    return next(t for t in templates.BUILT_IN if t["name"] == name)["doc"]


def walk(node, found):
    """Every entry under a "properties" key that has no description, except a block's type."""
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            for key, value in props.items():
                if key != "type" and "description" not in value:
                    found.append(key)
        for value in node.values():
            walk(value, found)
    elif isinstance(node, list):
        for value in node:
            walk(value, found)
    return found


def test_every_field_has_a_description():
    # Fails until the description subagents are merged in.
    assert walk(json.loads(SCHEMA.read_text()), []) == []


def test_post_refuses():
    client = user()
    bad = doc(grid="viel")
    res = client.post("/api/sheets", json={"title": "x", "doc": bad})
    assert res.status_code == 422
    assert res.json()["detail"] == {"problems": ["grid: must be a number, got a string"]}
    assert client.get("/api/sheets").json() == []


def test_patch_refuses():
    client = user()
    made = sheet(client, [text_block()])
    res = client.patch(
        f"/api/sheets/{made['id']}",
        json={"doc": doc(text_block(zauber=1), grid="viel"), "version": made["version"]},
    )
    assert res.status_code == 422
    problems_sent = res.json()["detail"]["problems"]
    assert any("zauber" in p for p in problems_sent)
    after = client.get(f"/api/sheets/{made['id']}").json()
    assert after["version"] == made["version"]
    assert after["doc"] == made["doc"]


def test_error_names_path_and_bound():
    maths = next(
        b for b in built_in("Rechenblatt Klasse 1")["pages"][0]["blocks"] if b["type"] == "maths"
    )
    maths = copy.deepcopy(maths)
    maths["props"]["columns"] = 9
    assert problems(doc(maths)) == ["pages[0].blocks[0].props.columns: must be 1 to 6, got 9"]


def test_unknown_type_names_allowed():
    types = json.loads(SCHEMA.read_text())["definitions"]["Block"]["properties"]["type"]["enum"]
    listed = ", ".join(f"'{t}'" for t in types)
    block = text_block()
    block["type"] = "zauber"
    assert problems(doc(block)) == [
        f"pages[0].blocks[0].type: must be one of {listed}, got 'zauber'"
    ]


def test_several_faults_listed():
    bad = doc(text_block(zauber=1), grid="viel", landscape="ja")
    listed = problems(bad)
    assert len(listed) == 3
    assert listed == sorted(listed, key=lambda p: p.split(":")[0])
    assert "grid: must be a number, got a string" in listed
    assert "landscape: must be a yes or no, got a string" in listed
    assert any("zauber" in p for p in listed)

    many = doc(*(dict(text_block(), type="zauber") for _ in range(12)))
    assert len(problems(many)) == 10


def test_builtin_templates_pass():
    for template in templates.BUILT_IN:
        sheet_doc = template["doc"]
        assert isinstance(sheet_doc, dict)
        assert problems(sheet_doc) == [], template["name"]


def test_template_post_refuses():
    client = user()
    res = client.post("/api/templates", json={"name": "x", "doc": doc(grid="viel")})
    assert res.status_code == 422
    assert client.get("/api/templates").json() == templates.BUILT_IN


def test_rename_unchecked():
    client = user()
    made = sheet(client, [text_block()])
    db.open_db().execute(
        "UPDATE sheets SET doc = ? WHERE id = ?",
        (json.dumps(doc(grid="viel")), made["id"]),
    )
    res = client.patch(f"/api/sheets/{made['id']}", json={"title": "Neu"})
    assert res.status_code == 200
    assert res.json()["title"] == "Neu"


def test_old_sheet_loads():
    client = user()
    made = sheet(client, [text_block()])
    db.open_db().execute(
        "UPDATE sheets SET doc = ? WHERE id = ?",
        (json.dumps(doc(grid="viel")), made["id"]),
    )
    assert client.get(f"/api/sheets/{made['id']}").status_code == 200


def test_corpus_passes():
    for path in sorted(CORPUS.glob("*.json")):
        assert problems(json.loads(path.read_text())["doc"]) == [], path.name
