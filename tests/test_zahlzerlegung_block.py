"""A Zahlzerlegung block does what every block can do: copy, group, cut, delete, move to page 2, odd stored props,
a save and a reload (#1078). It tests the block as a box and its stored props, not what it draws.

The docstrings name the checklist line that each test proves.
"""

from playwright.sync_api import expect
from test_zahlzerlegung import ZZ, fit
from ui import TEXT, at, box, doc, drawer, expect_picked, pick, reload, saved, thumb, user

ODD = {
    "count": -3,
    "columns": 99,
    "task": "x",
    "max": None,
    "typed": [[9, 9, 9], "a"],
    "seed": "s",
}
W, H = fit(ZZ)


def fields(z=1, **more):
    return box("k", "zahlzerlegung", ZZ, z=z, w=W, h=H, **more)


def text(**more):
    """A text well below the block, so that the two do not overlap."""
    return box("t", "text", TEXT, z=2, y=150, **more)


def stored(client, page):
    """The blocks of the first page as the server holds them, by name."""
    return {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}


def zzs(client, page):
    return [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "zahlzerlegung"]


def test_copy_and_paste_keep_type_and_props(editor):
    """Block actions (#1078): copy and paste keep type and props, the copy has another id."""
    client = user()
    page = editor(fields(), text(), client=client)
    pick(page, "k")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    copies = zzs(client, page)
    assert len(copies) == 2
    assert all(b["props"] == ZZ for b in copies)
    assert len({b["id"] for b in copies}) == 2


def test_grouped_with_a_text_both_keep_the_group_and_ungroup_frees_them(editor):
    """Block actions (#1078): grouped by Ctrl+G both carry one group id; Ctrl+Shift+G frees them."""
    client = user()
    page = editor(fields(), text(), client=client)
    pick(page, "k", "t")
    page.keyboard.press("Control+g")
    expect(page.locator(".block.sel")).to_have_count(2)
    groups = {b["id"]: b.get("group") for b in saved(page, client)}
    assert groups["k"] and groups["k"] == groups["t"]
    page.keyboard.press("Escape")
    at(page, "k").click()
    expect_picked(page, "k", "t")
    page.keyboard.press("Control+Shift+G")
    expect(page.locator(".block.sel")).to_have_count(2)
    assert not any(b.get("group") for b in saved(page, client) if b["id"] in ("k", "t"))


def test_delete_and_undo_brings_the_block_back_with_its_props(editor):
    """Block actions (#1078): Delete takes the block off, undo brings it back with the same props."""
    client = user()
    page = editor(fields(), text(), client=client)
    pick(page, "k")
    page.keyboard.press("Delete")
    expect(at(page, "k")).to_have_count(0)
    page.keyboard.press("Control+z")
    expect(at(page, "k")).to_have_count(1)
    assert stored(client, page)["k"]["props"] == ZZ


def test_cut_and_paste_keeps_the_type_and_props(editor):
    """Block actions (#1078): a cut and a paste move the block as it is, with its type and props."""
    client = user()
    page = editor(fields(), text(), client=client)
    pick(page, "k")
    page.keyboard.press("Control+x")
    expect(at(page, "k")).to_have_count(0)
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(2)
    found = zzs(client, page)
    assert len(found) == 1
    assert found[0]["props"] == ZZ


def test_moved_to_page_2_keeps_its_props(editor):
    """Block actions (#1078): a block cut on page 1 and pasted on page 2 keeps type and props there."""
    client = user()
    # theme="" opens the panel Seiten, which holds the page thumbnails.
    page = editor(
        fields(),
        text(),
        pages=[{"blocks": [box("u", "text", TEXT, z=1)]}],
        client=client,
        theme="",
        touch=True,
    )
    drawer(page, "left")
    pick(page, "k")
    page.keyboard.press("Control+x")
    expect(at(page, "k")).to_have_count(0)
    # thumb counts from 0: page 2 is thumb 1.
    thumb(page, 1).click()
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    second = doc(page, client)["pages"][1]["blocks"]
    assert [(b["type"], b["props"]) for b in second if b["type"] == "zahlzerlegung"] == [
        ("zahlzerlegung", ZZ)
    ]


def test_odd_stored_props_still_draw_and_the_panel_opens(editor):
    """Old sheets (#1078): odd stored props draw, no fault shows, and the panel opens; props {} too."""
    client = user()
    page = editor(
        box("odd", "zahlzerlegung", ODD, z=1, w=W, h=H),
        box("empty", "zahlzerlegung", {}, z=2, y=150, w=W, h=H),
        client=client,
    )
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    expect(at(page, "odd").locator(".zahlzerlegung")).to_be_visible()
    expect(at(page, "empty").locator(".zahlzerlegung")).to_be_visible()
    expect(page.locator(".fault")).to_have_count(0)
    pick(page, "odd")
    expect(
        page.locator(".panel").get_by_role("heading", name="Zahlzerlegung", exact=True)
    ).to_be_visible()
    assert not errors, errors


def test_a_reload_keeps_the_props_and_the_typed_numbers(editor):
    """Settings (#1078): after a reload the props and the typed numbers are as they were."""
    client = user()
    props = {**ZZ, "count": 3, "columns": 3, "max": 100, "task": "places", "typed": [[0, 37]]}
    page = editor(box("k", "zahlzerlegung", props, w=fit(props)[0], h=fit(props)[1]), client=client)
    pick(page, "k")
    reload(page, page.url)
    expect(at(page, "k").locator(".zahlzerlegung")).to_be_visible()
    assert stored(client, page)["k"]["props"] == props
