import copy
import io

import httpx
import pypdf
import pypdfium2
from fastapi.testclient import TestClient
from ui import LINE, RECT, RULING, TABLE, block, maths, serving, sheet, user

from blattwerk import pdf, variants
from blattwerk.app import app


def chromium(token):
    return TestClient(app, base_url="https://testserver", headers={"X-Render-Token": token})


def fixture(client):
    """A sheet with room: maths, Suchsel, Schüttelwörter, Lösungswörter and a plain text."""
    return sheet(
        client,
        [
            block("maths", 20, 60, maths(client, count=12, max=100)),
            block(
                "suchsel",
                90,
                80,
                {
                    "words": ["Hund", "Katze", "Maus", "Igel"],
                    "cols": 10,
                    "rows": 10,
                    "ways": "down",
                    "caps": True,
                    "umlauts": True,
                    "show": "words",
                    "seed": 5,
                },
            ),
            {
                **block(
                    "text",
                    180,
                    30,
                    {
                        "text": "Der Hund bellt laut im Garten",
                        "size": 14,
                        "align": "left",
                        "mix": 7,
                    },
                ),
                "id": "mix",
            },
            {
                **block(
                    "text",
                    215,
                    40,
                    {
                        "text": "Der Hund bellt laut im Garten",
                        "size": 14,
                        "align": "left",
                        "bank": 3,
                        "rich": [
                            {
                                "runs": [
                                    {"text": "Der "},
                                    {"text": "Hund", "gap": True},
                                    {"text": " bellt "},
                                    {"text": "laut", "gap": True},
                                    {"text": " im "},
                                    {"text": "Garten", "gap": True},
                                ]
                            }
                        ],
                    },
                ),
                "id": "bank",
            },
            {
                **block("text", 260, 10, {"text": "Name:", "size": 14, "align": "left"}),
                "id": "name",
            },
        ],
    )


def cookie(client):
    return {"Cookie": f"session={client.cookies['session']}"}


def texts(data: bytes) -> list[str]:
    return [page.extract_text() for page in pypdf.PdfReader(io.BytesIO(data)).pages]


def letters(page: str) -> list[str]:
    """The letter lines of a page: the variant's mark."""
    return [line.strip() for line in page.splitlines() if line.strip() in ("A", "B", "C", "D")]


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


def rows_cols(exercises: list[dict]) -> tuple[int, int]:
    """The most rows and columns of the written grids of some exercises."""
    grids = [e["grid"] for e in exercises if "grid" in e]
    return max((g["rows"] for g in grids), default=0), max((g["cols"] for g in grids), default=0)


def written_props(client, **more):
    return maths(client, ops=["*"], max=10000, format="written", count=6, rest=True, **more)


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


LUECKEN = ["Schiffahrt", "Katzenhaus", "Vogelnest", "Pferdestall", "Schulhof", "Blumenbeet"]


def word_lines(page: str) -> list[str]:
    """The lines of a page that hold words: not blank, not the variant's letter or the key mark."""
    lines = [line.strip() for line in page.splitlines()]
    return [
        line.replace(" ", "")
        for line in lines
        if line and line not in ("A", "B", "C", "D") and not line.startswith("Lösungen")
    ]


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


def grid(page: str) -> list[str]:
    """The rows of a Suchsel grid on a page: lines of ten capitals, spaces between them or not."""
    rows = [line.replace(" ", "") for line in page.splitlines()]
    return [row for row in rows if len(row) == 10 and row.isupper()]


SENTENCE = "Der Hund bellt laut im Garten"


def mix_line(page: str) -> str:
    """The Schüttelwörter line of a page: the sentence's letters in another order."""
    key = sorted(SENTENCE.replace(" ", ""))
    lines = [line for line in page.splitlines() if sorted(line.replace(" ", "")) == key]
    lines = [line for line in lines if line != SENTENCE]
    assert len(lines) == 1, lines
    return lines[0]


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


def picture(data: bytes, page: int) -> bytearray:
    """The pixels of a page, with its bottom right corner (20 by 12 mm) made blank."""
    bitmap = pypdfium2.PdfDocument(data)[page].render(scale=2, rev_byteorder=True)
    per_mm = 2 * 72 / 25.4
    cut_x = bitmap.width - round(20 * per_mm)
    cut_y = bitmap.height - round(12 * per_mm)
    out = bytearray(bitmap.buffer)
    for row in range(cut_y, bitmap.height):
        start = row * bitmap.stride
        out[start + cut_x * 3 : start + bitmap.width * 3] = b"\0" * ((bitmap.width - cut_x) * 3)
    return out


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
