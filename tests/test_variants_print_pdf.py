"""A set of variants prints the sheet once each, and variant A is the stored sheet."""

import copy

import httpx
from test_variants_print import (
    chromium,
    cookie,
    fixture,
    letters,
    texts,
)
from ui import (
    LINE,
    RECT,
    RULING,
    TABLE,
    block,
    maths,
    serving,
    sheet,
    user,
)

from blattwerk import (
    pdf,
    variants,
)


def test_a_pdf_of_three_variants_holds_the_sheet_three_times_a_first():
    """A1: `varianten=3` prints one sheet per letter, in order A, B, C."""
    client = user()
    mine = sheet(client, [block("text", 20, 20, {"text": "Name:", "size": 14, "align": "left"})])
    with serving() as server:
        res = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf?varianten=3", headers=cookie(client), timeout=120
        )
    assert res.status_code == 200
    pages = texts(res.content)
    assert len(pages) == 3
    assert [letters(p) for p in pages] == [["A"], ["B"], ["C"]]


def test_a_variant_is_the_same_on_every_run_and_differs_from_a():
    """A3: B is the same on every run; its maths differ from A and C; its seeds are `derived`."""
    client = user()
    doc = fixture(client)["doc"]
    first = variants.vary(doc, "B")[0]
    assert first == variants.vary(doc, "B")[0]
    b = first["pages"][0]["blocks"][0]["props"]
    a = doc["pages"][0]["blocks"][0]["props"]
    c = variants.vary(doc, "C")[0]["pages"][0]["blocks"][0]["props"]
    assert b["exercises"] != a["exercises"]
    assert b["exercises"] != c["exercises"]
    assert b["seed"] == variants.derived(a["seed"], "B")


def test_every_seeded_block_changes_and_a_block_with_no_seed_stays():
    """A4: seeded blocks change for B; unseeded blocks stay; bad seeds do not raise."""
    client = user()
    doc = fixture(client)["doc"]
    b, _ = variants.vary(doc, "B")
    by = {blk["id"]: blk for blk in doc["pages"][0]["blocks"]}
    got = {blk["id"]: blk for blk in b["pages"][0]["blocks"]}
    assert got["maths"]["props"]["exercises"] != by["maths"]["props"]["exercises"]
    assert got["suchsel"]["props"]["seed"] != 5
    assert got["mix"]["props"]["mix"] != 7
    assert got["bank"]["props"]["bank"] != 3
    assert got["name"] == by["name"]
    # Blocks with no seed, and a group with a plain text, are left as stored; a grouped maths
    # block with a seed still changes.
    extra = copy.deepcopy(doc)
    maths_block = copy.deepcopy(doc["pages"][0]["blocks"][0])
    rest = [
        {**block("shape", 0, 1, LINE), "id": "line"},
        {**block("shape", 0, 10, RECT), "id": "rect"},
        {**block("ruling", 0, 10, RULING), "id": "rule"},
        {**block("table", 0, 10, TABLE), "id": "table"},
        {**block("image", 0, 10, {"upload": 1, "ratio": 1.5, "cut": [0, 0, 0, 0]}), "id": "photo"},
        {
            **block("text", 0, 10, {"text": "Gruppe", "size": 14, "align": "left"}),
            "id": "gtext",
            "group": ["g1"],
        },
        {**maths_block, "id": "gmaths", "group": ["g1"]},
    ]
    extra["pages"][0]["blocks"] += rest
    out = {blk["id"]: blk for blk in variants.vary(extra, "B")[0]["pages"][0]["blocks"]}
    for blk in rest:
        if blk["id"] != "gmaths":
            assert out[blk["id"]] == blk, blk["id"]
    assert out["gmaths"]["props"]["seed"] != maths_block["props"]["seed"]
    # A table's bank and a text's holeSeed change.
    by_id = {blk["id"]: blk for blk in extra["pages"][0]["blocks"]}
    by_id["table"]["props"]["bank"] = 4
    by_id["bank"]["props"]["holeSeed"] = 9
    out = {blk["id"]: blk for blk in variants.vary(extra, "B")[0]["pages"][0]["blocks"]}
    assert out["table"]["props"]["bank"] != 4
    assert out["bank"]["props"]["holeSeed"] != 9
    # Strange seeds and documents do not raise.
    odd = {
        "pages": [
            {
                "blocks": [
                    {"id": "s", "type": "suchsel", "props": {"seed": "5"}},
                    {"id": "f", "type": "suchsel", "props": {"seed": 2.5}},
                ]
            }
        ]
    }
    assert variants.vary(odd, "B")[0]["pages"][0]["blocks"][0]["props"]["seed"] == "5"
    assert variants.vary({}, "B") == ({}, [])
    assert variants.vary({"pages": "x"}, "B")[0] == {"pages": "x"}


def test_each_page_of_a_variant_carries_its_letter_and_the_switch_hides_it():
    """A5: each page shows its letter; `buchstaben=false` hides it; the key keeps its letter."""
    client = user()
    mine = sheet(client, [block("text", 20, 20, {"text": "Name:", "size": 14, "align": "left"})])
    with serving() as server:
        on = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf?varianten=2", headers=cookie(client), timeout=120
        )
        off = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf?varianten=2&buchstaben=false",
            headers=cookie(client),
            timeout=120,
        )
        key = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf?solved=true&varianten=2&buchstaben=false",
            headers=cookie(client),
            timeout=120,
        )
    assert [letters(p) for p in texts(on.content)] == [["A"], ["B"]]
    assert all(letters(p) == [] for p in texts(off.content))
    keys = " ".join(texts(key.content))
    assert "Lösungen A" in keys and "Lösungen B" in keys
    first, second = texts(key.content)
    assert "Lösungen A" in first and "Lösungen B" not in first
    assert "Lösungen B" in second and "Lösungen A" not in second


def test_a_variant_that_cannot_fill_a_block_prints_nothing_and_names_the_block(monkeypatch):
    """A7: a block the variant cannot fill gives 409 with its name; the variant route lists it."""
    client = user()
    mine = fixture(client)
    monkeypatch.setattr(variants, "generate", lambda s: {"exercises": [], "loosen": ["max"]})
    with serving() as server:
        res = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf?varianten=2", headers=cookie(client), timeout=60
        )
    assert res.status_code == 409
    assert res.json()["detail"]["short"] == [
        {"page": 1, "id": "maths", "type": "maths", "letter": "B"}
    ]
    got = client.get(f"/api/sheets/{mine['id']}/variante/B").json()
    assert got["short"] == [{"page": 1, "id": "maths", "type": "maths"}]
    assert got["doc"]["pages"][0]["blocks"][0] == mine["doc"]["pages"][0]["blocks"][0]


def test_a_maths_block_the_generator_refuses_is_short_and_does_not_raise():
    """A7b: stored props that fail validation make the block short, not an error."""
    doc = {
        "pages": [
            {
                "blocks": [
                    {
                        "id": "maths",
                        "type": "maths",
                        "props": {"ops": ["+"], "max": 0, "count": 3, "seed": 4, "exercises": []},
                    }
                ]
            }
        ]
    }
    _, short = variants.vary(doc, "B")
    assert short == [{"page": 1, "id": "maths", "type": "maths"}]


def test_one_variant_is_the_pdf_of_today(monkeypatch):
    """A10a: `variante=A` is the stored doc; `varianten=1` prints as today, without `vary`."""
    client = user()
    mine = fixture(client)
    token = pdf.new_token(mine["id"])
    assert chromium(token).get(f"/api/render/{mine['id']}?variante=A").json() == mine["doc"]
    with serving() as server:
        plain = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf", headers=cookie(client), timeout=120
        )
        one = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf?varianten=1", headers=cookie(client), timeout=120
        )
    assert texts(plain.content) == texts(one.content)
    assert len(texts(plain.content)) == len(texts(one.content))
    assert all(letters(p) == [] for p in texts(one.content))

    def boom(*args):
        raise AssertionError("not for the old path")

    monkeypatch.setattr(variants, "vary", boom)
    with serving() as server:
        again = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf?varianten=1", headers=cookie(client), timeout=120
        )
        plain_again = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf", headers=cookie(client), timeout=120
        )
        solved = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf?solved=true", headers=cookie(client), timeout=120
        )
    assert again.status_code == 200
    assert plain_again.status_code == 200
    assert solved.status_code == 200


def test_variant_a_in_a_set_is_the_stored_tasks_word_for_word():
    """A10b: A keeps hand-written exercises; page 1 of a set shows them, page 2 does not."""
    client = user()
    ex = [{"op": "+", "a": 1, "b": 1, "result": 2, "rest": 0}] * 3
    blk = block("maths", 20, 60, maths(client, count=3, max=20))
    blk["props"]["exercises"] = ex
    doc = {"pages": [{"blocks": [blk]}], "guides": {"x": [], "y": []}, "grid": 0}
    assert variants.vary(doc, "A")[0] is doc
    mine = client.post("/api/sheets", json={"title": "Plus", "doc": doc}).json()
    with serving() as server:
        res = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf?varianten=2", headers=cookie(client), timeout=120
        )
    pages = texts(res.content)
    assert "1 + 1" in pages[0]
    assert "1 + 1" not in pages[1]
