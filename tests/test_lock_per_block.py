"""The ratio lock is kept per block: each block remembers its own, and the sheet saves it."""

import pytest
from playwright.sync_api import expect
from test_fields import by_id, enter, field, lock
from ui import RECT, box, centre, drag, pick, reload, saved, user

# A rect with room around it to move and grow in.
ROOM = {"x": 40, "y": 60, "w": 80, "h": 40}
# The second block, beside the first.
BESIDE = {"x": 150, "y": 60, "w": 80, "h": 40}


def test_the_lock_is_each_blocks_own_when_another_is_picked(editor):
    page = editor(box("a", "shape", RECT, **ROOM), box("b", "shape", RECT, z=2, **BESIDE))
    pick(page, "a")
    lock(page).click()
    expect(lock(page)).to_have_attribute("aria-pressed", "true")
    pick(page, "b")
    expect(lock(page)).to_have_attribute("aria-pressed", "false")
    pick(page, "a")
    expect(lock(page)).to_have_attribute("aria-pressed", "true")


def test_the_lock_stays_on_its_block_after_a_reload(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, **ROOM), box("b", "shape", RECT, z=2, **BESIDE), client=client
    )
    pick(page, "a")
    lock(page).click()
    expect(lock(page)).to_have_attribute("aria-pressed", "true")
    saved(page, client)
    reload(page, page.url)
    pick(page, "a")
    expect(lock(page)).to_have_attribute("aria-pressed", "true")
    pick(page, "b")
    expect(lock(page)).to_have_attribute("aria-pressed", "false")
    blocks = by_id(saved(page, client))
    assert blocks["a"]["keep"] is True
    assert "keep" not in blocks["b"]


def test_a_sheet_without_the_key_opens_unlocked_and_keeps_its_stored_form(editor):
    client = user()
    page = editor(box("a", "shape", RECT, **ROOM), client=client)
    pick(page, "a")
    expect(lock(page)).to_have_attribute("aria-pressed", "false")
    enter(page, "Breite", "100")
    expect(field(page, "Breite")).to_have_value("100")
    expect(field(page, "Höhe")).to_have_value("40")
    (a,) = saved(page, client)
    assert (a["w"], a["h"]) == (100, 40)
    assert "keep" not in a


def test_switching_the_lock_is_one_undo_step(editor):
    client = user()
    page = editor(box("a", "shape", RECT, **ROOM), client=client)
    pick(page, "a")
    before = saved(page, client)
    lock(page).click()
    expect(lock(page)).to_have_attribute("aria-pressed", "true")
    saved(page, client)
    page.get_by_label("Rückgängig", exact=True).click()
    expect(lock(page)).to_have_attribute("aria-pressed", "false")
    assert saved(page, client) == before


def test_switching_the_lock_off_removes_the_key_from_the_sheet(editor):
    client = user()
    page = editor(box("a", "shape", RECT, **ROOM), client=client)
    pick(page, "a")
    lock(page).click()
    expect(lock(page)).to_have_attribute("aria-pressed", "true")
    saved(page, client)
    lock(page).click()
    expect(lock(page)).to_have_attribute("aria-pressed", "false")
    (a,) = saved(page, client)
    assert "keep" not in a


def test_the_lock_of_two_picked_blocks_keeps_both_ratios(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, **ROOM), box("b", "shape", RECT, z=2, **BESIDE), client=client
    )
    pick(page, "a", "b")
    lock(page).click()
    expect(lock(page)).to_have_attribute("aria-pressed", "true")
    blocks = by_id(saved(page, client))
    assert blocks["a"]["keep"] is True
    assert blocks["b"]["keep"] is True


def test_a_locked_block_keeps_its_ratio_when_its_corner_is_dragged(editor):
    page = editor(box("a", "shape", RECT, **ROOM))
    pick(page, "a")
    enter(page, "Breite", "100")
    lock(page).click()
    expect(lock(page)).to_have_attribute("aria-pressed", "true")
    x, y = centre(page.locator(".moveable-control.moveable-se"))
    drag(page, (x, y), (x + 60, y))
    expect(field(page, "Breite")).not_to_have_value("100")
    width, height = (
        float(field(page, n).input_value().replace(",", ".")) for n in ("Breite", "Höhe")
    )
    assert width / height == pytest.approx(2.5, rel=0.02)


def test_copy_and_paste_carry_the_lock(editor):
    client = user()
    page = editor(box("a", "shape", RECT, **ROOM), client=client)
    pick(page, "a")
    lock(page).click()
    expect(lock(page)).to_have_attribute("aria-pressed", "true")
    saved(page, client)
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block")).to_have_count(2)
    blocks = saved(page, client)
    kept = [b for b in blocks if b["id"] != "a"]
    assert len(kept) == 1
    assert kept[0]["keep"] is True
