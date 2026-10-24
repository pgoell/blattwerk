"""A written variant fits in the stored block, and each key belongs to its own tasks."""

import httpx
from fastapi.testclient import TestClient
from test_variants_print import (
    LUECKEN,
    SENTENCE,
    chromium,
    cookie,
    fixture,
    grid,
    mix_line,
    picture,
    rows_cols,
    texts,
    word_lines,
    written_props,
)
from ui import (
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
from blattwerk.app import app


def test_a_written_variant_never_needs_more_room_than_the_stored_block():
    """A7/B1: a written variant fits the stored block's grid, or is short; a later try can win."""
    client = user()
    cases = [
        maths(client, ops=["/"], max=10000, format="written", count=6, rest=True, seed=s)
        for s in range(20, 40)
    ] + [written_props(client, seed=s) for s in range(10)]
    total = short = later = 0
    for props in cases:
        doc = {"pages": [{"blocks": [{"id": "m", "type": "maths", "props": props}]}]}
        stored_rows, stored_cols = rows_cols(props["exercises"])
        for letter in "BCD":
            out, gone = variants.vary(doc, letter)
            total += 1
            made = out["pages"][0]["blocks"][0]["props"]
            if gone:
                short += 1
                assert gone == [{"page": 1, "id": "m", "type": "maths"}]
                assert made == props
                continue
            rows, cols = rows_cols(made["exercises"])
            assert rows <= stored_rows and cols <= stored_cols, (props["seed"], letter)
            later += made["seed"] != variants.derived(props["seed"], letter)
    assert later >= 1
    # With a hundred tries each of these blocks finds its variants.
    assert short == 0, (short, total)


def test_a_variant_that_took_a_later_try_is_the_same_on_every_run():
    """A7/B2: a variant that took a later try gives the same document on every run."""
    client = user()
    for s in range(20, 40):
        props = maths(client, ops=["/"], max=10000, format="written", count=6, rest=True, seed=s)
        doc = {"pages": [{"blocks": [{"id": "m", "type": "maths", "props": props}]}]}
        for letter in "BCD":
            first = variants.vary(doc, letter)[0]
            if first["pages"][0]["blocks"][0]["props"]["seed"] != variants.derived(s, letter):
                assert first == variants.vary(doc, letter)[0]
                return
    raise AssertionError("no variant took a later try")


def test_a_written_block_repeated_keeps_its_room_in_the_pdf():
    """A7/B3: the written block of seed 24, whose plain variants B and C need more rows than its
    60 mm hold, prints in four variants: each took a try that fits."""
    client = user()
    mine = sheet(client, [block("maths", 20, 60, written_props(client, seed=24))])
    with serving() as server:
        res = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf?varianten=4", headers=cookie(client), timeout=120
        )
    assert res.status_code == 200
    assert len(texts(res.content)) == 4
    stored = mine["doc"]["pages"][0]["blocks"][0]["props"]["exercises"]
    for letter in "BCD":
        made = variants.vary(mine["doc"], letter)[0]["pages"][0]["blocks"][0]["props"]["exercises"]
        assert made != stored
        assert all(a <= b for a, b in zip(rows_cols(made), rows_cols(stored), strict=True))


def test_the_key_of_lueckenwoerter_belongs_to_its_variant():
    """A6: each gapped word keeps its letters in order from its key word, and sheets B differ."""
    client = user()
    listed = {
        "text": "",
        "size": 14,
        "align": "left",
        "list": True,
        "holes": "one",
        "holeSeed": 7,
    }
    mine = sheet(client, [block("text", 20, 120, listed)], words=LUECKEN)
    with serving() as server:
        sheet_pdf = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf?varianten=3", headers=cookie(client), timeout=120
        )
        key_pdf = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf?solved=true&varianten=3",
            headers=cookie(client),
            timeout=120,
        )
    sheets, keys = texts(sheet_pdf.content), texts(key_pdf.content)
    assert len(sheets) == len(keys) == 3
    gapped = []
    for i in range(3):
        sheet_words = word_lines(sheets[i])
        key_words = word_lines(keys[i])
        assert len(sheet_words) == len(key_words) == len(LUECKEN)
        for s, k in zip(sheet_words, key_words, strict=True):
            assert k in LUECKEN and len(s) < len(k)
            # The kept letters, in order, are a part of the full word.
            rest = iter(k)
            assert all(ch in rest for ch in s), (i, s, k)
        gapped.append(sheet_words)
    assert gapped[0] != gapped[1]


def test_each_key_belongs_to_its_own_tasks():
    """A6: each key page holds the tasks, grid, words and sentence of its sheet page; B differs."""
    client = user()
    mine = fixture(client)
    mixed = []
    with serving() as server:
        sheet_pdf = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf?varianten=3", headers=cookie(client), timeout=120
        )
        key_pdf = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf?solved=true&varianten=3",
            headers=cookie(client),
            timeout=120,
        )
    sheets, keys = texts(sheet_pdf.content), texts(key_pdf.content)
    assert len(sheets) == len(keys) == 3
    for i in range(3):
        sums = [line.split("=")[0].strip() for line in sheets[i].splitlines() if "=" in line]
        assert sums
        for left in sums:
            assert any(left in line for line in keys[i].splitlines()), (i, left)
        assert grid(sheets[i]) == grid(keys[i])
        # The word box of the sheet, in its order, is the one the key shows.
        box = [line for line in sheets[i].splitlines() if "Garten" in line and "Der" not in line]
        assert len(box) == 1 and box[0] in keys[i].splitlines(), (i, box)
        mixed.append(mix_line(sheets[i]))
        assert SENTENCE in keys[i].splitlines()
    assert [line for line in sheets[0].splitlines() if "=" in line] != [
        line for line in sheets[1].splitlines() if "=" in line
    ]
    assert grid(sheets[0]) != grid(sheets[1])
    assert mixed[0] != mixed[1]
    # The same settings print the same pages on every run.
    with serving() as server:
        again = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf?varianten=3", headers=cookie(client), timeout=120
        )
    assert texts(again.content) == sheets


def test_the_pages_of_a_in_a_set_equal_the_plain_pdf_but_for_the_letter():
    """A10c: page 1 of a set is the plain PDF but for its letter, and the set has two sheets."""
    client = user()
    mine = fixture(client)
    with serving() as server:
        plain = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf", headers=cookie(client), timeout=120
        )
        two = httpx.get(
            f"{server}/api/sheets/{mine['id']}/pdf?varianten=2", headers=cookie(client), timeout=120
        )
    plain_text, two_text = texts(plain.content), texts(two.content)
    assert len(two_text) == 2 * len(plain_text)
    first = [line for line in two_text[0].splitlines() if line.strip() != "A"]
    assert first == plain_text[0].splitlines()
    assert picture(plain.content, 0) == picture(two.content, 0)


def test_access_is_for_the_owner_and_the_token_only():
    """Access: another user gets 404, no token 404, and out-of-range letters or counts 422."""
    client = user()
    mine = sheet(client, [])
    stranger = user()
    assert stranger.get(f"/api/sheets/{mine['id']}/variante/B").status_code == 404
    assert (
        chromium(pdf.new_token(mine["id"])).get(f"/api/render/{mine['id']}?variante=B").status_code
        == 200
    )
    assert TestClient(app).get(f"/api/render/{mine['id']}?variante=B").status_code == 404
    assert client.get(f"/api/sheets/{mine['id']}/variante/E").status_code == 404
    assert client.get(f"/api/sheets/{mine['id']}/variante/AB").status_code == 404
    assert client.get(f"/api/sheets/{mine['id']}/pdf?varianten=5").status_code == 422
    assert (
        chromium(pdf.new_token(mine["id"])).get(f"/api/render/{mine['id']}?variante=E").status_code
        == 422
    )
