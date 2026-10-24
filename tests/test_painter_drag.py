"""Dragging the brush paints the words it crosses and leaves the block where it is."""

import pytest
from playwright.sync_api import expect
from test_painter import (
    BOLD_RED,
    brush,
    drag,
    expect_brush,
    group_texts,
    held,
    painted,
    saved_x,
    saved_xs,
    word,
)
from ui import (
    FIELD,
    LINE,
    RECT,
    TEXT,
    at,
    box,
    caret,
    expect_picked,
    pick,
    picture,
    saved,
    stopped,
    unpick,
    upload,
    user,
)


def test_a_drag_paints_only_the_words_it_crosses(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "text": "Hallo Welt", "rich": BOLD_RED}),
        box("b", "text", {**TEXT, "text": "eins zwei drei"}, z=2),
        client=client,
    )
    caret(page, "Hallo", 2)
    brush(page).click()
    expect_brush(page, True)
    drag(page, "b", "zwei")
    expect_brush(page, False)
    b = held(page, client)["b"]
    # Only the dragged word takes the bold and the red, the rest of the text keeps its own look.
    assert b.get("bold") is not True and b.get("color") != "#ff0000"
    assert painted(b) == [("zwei", True, "#ff0000")]


def test_ctrl_shift_c_in_an_open_text_copies_the_word_look(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "text": "Hallo Welt", "rich": BOLD_RED}),
        box("b", "text", {**TEXT, "text": "du"}, z=2),
        client=client,
    )
    caret(page, "Hallo", 2)
    assert stopped(page, "Control+Shift+C")
    # The field stays open and focused, and nothing reaches the system clipboard.
    expect(page.locator(FIELD)).to_be_focused()
    assert page.evaluate("localStorage.getItem('clip')") is None
    pick(page, "b")
    page.keyboard.press("Control+Shift+V")
    expect_picked(page, "b")
    b = held(page, client)["b"]
    assert b["bold"] is True and b["color"] == "#ff0000"


def test_ctrl_shift_v_in_an_open_text_paints_the_picked_words(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "text": "Hallo Welt", "rich": BOLD_RED}),
        box("b", "text", {**TEXT, "text": "eins zwei drei"}, z=2),
        client=client,
    )
    caret(page, "Hallo", 2)
    assert stopped(page, "Control+Shift+C")
    pick(page, "b")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Home")
    for _ in range(5):
        page.keyboard.press("ArrowRight")
    for _ in range(4):
        page.keyboard.press("Shift+ArrowRight")
    text = page.locator(FIELD).inner_text()
    assert stopped(page, "Control+Shift+V")
    expect(page.locator(f"{FIELD} span[data-bold]")).to_have_text("zwei")
    # The keys paste no text into the field.
    assert page.locator(FIELD).inner_text() == text
    expect(page.locator(FIELD)).to_be_focused()
    unpick(page)
    b = held(page, client)["b"]
    assert painted(b) == [("zwei", True, "#ff0000")]


def test_a_drag_paint_is_one_undo_step(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "text": "Hallo Welt", "rich": BOLD_RED}),
        box("b", "text", {**TEXT, "text": "eins zwei drei"}, z=2),
        client=client,
    )
    caret(page, "Hallo", 2)
    brush(page).click()
    drag(page, "b", "zwei")
    expect(page.get_by_label("Rückgängig")).to_be_enabled()
    page.get_by_label("Rückgängig").click()
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
    assert painted(held(page, client)["b"]) == []


def test_a_brush_drag_in_an_open_text_paints_its_words_and_keeps_the_block(editor):
    client = user()
    page = editor(box("a", "text", {**TEXT, "text": "Der Hund ist braun und klein"}), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Home")
    page.keyboard.press("Control+ArrowRight")
    page.keyboard.press("Control+Shift+ArrowRight")
    page.keyboard.press("Control+b")
    expect(page.locator(f"{FIELD} span[data-bold]")).to_have_text("Hund")
    x = saved_x(page, client)
    brush(page).click()
    expect_brush(page, True)
    drag(page, "a", "braun")
    expect_brush(page, False)
    assert saved_x(page, client) == x
    bold = {word.strip() for word, is_bold, _ in painted(held(page, client)["a"]) if is_bold}
    assert bold == {"Hund", "braun"}
    page.keyboard.press("Control+z")
    assert saved_x(page, client) == x
    bold = {word.strip() for word, is_bold, _ in painted(held(page, client)["a"]) if is_bold}
    assert bold == {"Hund"}


def test_a_brush_from_a_caret_in_a_text_opened_again_paints_the_words_it_crosses_in_place(editor):
    """#756, as the issue has it: the bold is saved, the text opened again, the caret in it."""
    client = user()
    runs = [{"text": "Der "}, {"text": "Hund", "bold": True}, {"text": " ist braun und klein"}]
    props = {**TEXT, "text": "Der Hund ist braun und klein", "rich": [{"runs": runs}]}
    page = editor(box("a", "text", props), client=client)
    x = saved_x(page, client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    w = word(page, "a", "Hund")
    page.mouse.click((w["x"] + w["right"]) / 2, w["y"])
    brush(page).click()
    expect_brush(page, True)
    drag(page, "a", "braun")
    expect_brush(page, False)
    assert saved_x(page, client) == x
    bold = {word.strip() for word, is_bold, _ in painted(held(page, client)["a"]) if is_bold}
    assert bold == {"Hund", "braun"}
    page.keyboard.press("Control+z")
    assert saved_x(page, client) == x
    bold = {word.strip() for word, is_bold, _ in painted(held(page, client)["a"]) if is_bold}
    assert bold == {"Hund"}


def test_a_kept_brush_on_a_picked_group_paints_it_once_and_keeps_the_group_picked(editor):
    """#756: a press on a picked text goes to the brush first; the click after picks no more."""
    client = user()
    group = {"group": ["g"]}
    page = editor(
        box("q", "text", {**TEXT, "text": "Quelle", "bold": True}, w=25),
        box("a", "text", {**TEXT, "text": "eins"}, z=2, w=25, **group),
        box("b", "text", {**TEXT, "text": "zwei"}, z=3, w=25, **group),
        client=client,
    )
    pick(page, "q")
    brush(page).dblclick()
    expect_brush(page, True)
    at(page, "a").click()
    expect_picked(page, "a", "b")
    # The group's frame lies over the picked block: the press goes where a hand would put it.
    at(page, "a").click(force=True)
    expect(brush(page)).to_have_attribute("aria-pressed", "true")
    expect_picked(page, "a", "b")
    assert held(page, client)["a"].get("bold") and held(page, client)["b"].get("bold")
    page.keyboard.press("Escape")
    page.keyboard.press("Control+z")
    expect(at(page, "a").locator("p").first).not_to_have_css("font-weight", "700")
    assert not held(page, client)["a"].get("bold") and not held(page, client)["b"].get("bold")


@pytest.mark.parametrize("group", [["g"], ["g", "inner"]], ids=["group", "nested"])
def test_a_brush_drag_across_words_of_a_text_in_a_picked_group_paints_them_and_keeps_the_group(
    editor, group
):
    """#761: the press lands on the group's frame; the words it crosses still take the look."""
    client = user()
    page = editor(*group_texts(client, group, extra=len(group) > 1), client=client)
    xs = saved_xs(page, client)
    # A click on "a" picks its outer group too: "c" comes along when "inner" is nested in "g".
    picked = ("a", "b", "c") if len(group) > 1 else ("a", "b")
    at(page, "a").click()
    expect_picked(page, *picked)
    brush(page).click()
    expect_brush(page, True)
    drag(page, "b", "zwei")
    expect_brush(page, False)
    # The text is open alone in its group, as PowerPoint picks a text inside a group.
    expect_picked(page, "b")
    assert saved_xs(page, client) == xs
    bold = {word.strip() for word, is_bold, _ in painted(held(page, client)["b"]) if is_bold}
    assert bold == {"zwei"}
    # The other texts of the group keep their own words.
    texts = {name: props["text"] for name, props in held(page, client).items()}
    others = {"c": "fern"} if len(group) > 1 else {}
    assert texts == {"a": "eins", "b": "eins zwei drei", **others}
    page.keyboard.press("Control+z")
    assert saved_xs(page, client) == xs
    bold = {word.strip() for word, is_bold, _ in painted(held(page, client)["b"]) if is_bold}
    assert bold == set()


def test_a_brush_drag_on_a_locked_text_paints_it_whole_and_opens_no_field(editor):
    """A locked text takes no words: the drag paints the block, as a click does."""
    client = user()
    page = editor(
        box("q", "text", {**TEXT, "text": "Quelle", "bold": True}, w=25),
        box("a", "text", {**TEXT, "text": "eins zwei drei"}, z=2, w=25, y=120, locked=True),
        client=client,
    )
    pick(page, "q")
    brush(page).click()
    expect_brush(page, True)
    drag(page, "a", "zwei")
    expect_brush(page, False)
    expect(page.locator(FIELD)).to_have_count(0)
    a = held(page, client)["a"]
    assert (a["text"], a.get("bold"), painted(a)) == ("eins zwei drei", True, [])


def test_a_brush_drag_with_ctrl_across_a_text_in_a_picked_group_makes_no_copy(editor):
    """#761: as #756, with Ctrl held; Moveable must not copy the group."""
    client = user()
    page = editor(*group_texts(client, ["g"]), client=client)
    xs = saved_xs(page, client)
    at(page, "a").click()
    expect_picked(page, "a", "b")
    brush(page).click()
    expect_brush(page, True)
    w = word(page, "b", "zwei")
    page.keyboard.down("Control")
    page.mouse.move(w["x"] + 1, w["y"])
    page.mouse.down()
    page.mouse.move(w["right"] - 1, w["y"], steps=5)
    page.mouse.up()
    page.keyboard.up("Control")
    expect(page.locator(".block")).to_have_count(2)
    assert saved_xs(page, client) == xs


def test_a_plain_look_takes_bold_and_red_off_the_words(editor):
    client = user()
    runs = [{"text": "eins "}, {"text": "zwei", "bold": True, "color": "#ff0000"}]
    rich = [{"runs": [*runs, {"text": " drei"}]}]
    page = editor(
        box("a", "text", TEXT),
        box("b", "text", {**TEXT, "text": "eins zwei drei", "rich": rich}, z=2),
        client=client,
    )
    pick(page, "a")
    brush(page).click()
    expect_brush(page, True)
    drag(page, "b", "zwei")
    expect_brush(page, False)
    # The words lose their bold and red: a block with no colour of its own has the default ink.
    left = painted(held(page, client)["b"])
    assert [look for look in left if look[1] or look[2] == "#ff0000"] == []


def test_a_double_click_keeps_the_brush_for_each_drag(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "bold": True, "color": "#ff0000"}),
        box("b", "text", {**TEXT, "text": "eins zwei drei"}, z=2),
        client=client,
    )
    pick(page, "a")
    brush(page).dblclick()
    expect_brush(page, True)
    drag(page, "b", "zwei")
    expect_brush(page, True)
    drag(page, "b", "drei")
    expect_brush(page, True)
    page.keyboard.press("Escape")
    expect_brush(page, False)
    red = [("zwei", True, "#ff0000"), ("drei", True, "#ff0000")]
    assert painted(held(page, client)["b"]) == red


def test_a_drag_over_a_line_or_a_picture_paints_the_whole_block(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "stroke": "#0000ff", "strokeWidth": 2}),
        box("l", "shape", LINE, z=2),
        box("p", "image", picture(upload(client))["props"], z=3),
        client=client,
    )
    pick(page, "a")
    brush(page).click()
    expect_brush(page, True)
    # A line has no words: the drag over it paints it whole, as a click does.
    box_ = at(page, "l").bounding_box()
    # Along the middle of the line: its box is wider than what it draws.
    page.mouse.move(box_["x"] + box_["width"] * 0.3, box_["y"] + box_["height"] / 2)
    page.mouse.down()
    page.mouse.move(box_["x"] + box_["width"] * 0.7, box_["y"] + box_["height"] / 2, steps=5)
    page.mouse.up()
    expect_picked(page, "l")
    expect_brush(page, False)
    assert held(page, client)["l"]["stroke"] == "#0000ff"
    # A picture has no words either: the same drag leaves it picked, and the brush spent.
    brush(page).click()
    expect_brush(page, True)
    box_ = at(page, "p").bounding_box()
    page.mouse.move(box_["x"] + box_["width"] * 0.3, box_["y"] + box_["height"] / 2)
    page.mouse.down()
    page.mouse.move(box_["x"] + box_["width"] * 0.7, box_["y"] + box_["height"] / 2, steps=5)
    page.mouse.up()
    expect_picked(page, "p")
    expect_brush(page, False)


def test_a_drag_on_a_shape_with_text_paints_its_words(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "bold": True, "color": "#ff0000"}),
        box("b", "shape", {**RECT, "text": "eins zwei drei"}, z=2),
        client=client,
    )
    pick(page, "a")
    brush(page).click()
    drag(page, "b", "zwei")
    expect_brush(page, False)
    assert painted(held(page, client)["b"]) == [("zwei", True, "#ff0000")]


def test_a_drag_with_a_lines_look_leaves_the_words_as_they_are(editor):
    """A line's look has nothing of words: a drag with it keeps a bold red word's own."""
    client = user()
    page = editor(
        box("l", "shape", LINE),
        box("b", "text", {**TEXT, "text": "Hallo Welt", "rich": BOLD_RED}, z=2),
        client=client,
    )
    pick(page, "l")
    brush(page).click()
    expect_brush(page, True)
    drag(page, "b", "Hallo")
    expect_brush(page, False)
    assert painted(held(page, client)["b"]) == [("Hallo", True, "#ff0000")]


def test_a_drag_the_window_loses_paints_nothing_then_or_later(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "bold": True}),
        box("b", "text", {**TEXT, "text": "eins zwei drei"}, z=2),
        box("c", "text", TEXT, z=3),
        client=client,
    )
    pick(page, "a")
    brush(page).click()
    w = word(page, "b", "zwei")
    page.mouse.move(w["x"] + 1, w["y"])
    page.mouse.down()
    page.mouse.move(w["right"] - 1, w["y"], steps=5)
    # The window loses the focus with the button still down: the drag is over.
    page.evaluate("dispatchEvent(new Event('blur'))")
    page.mouse.up()
    pick(page, "c")
    expect_picked(page, "c")
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
    assert held(page, client)["b"] == {**TEXT, "text": "eins zwei drei"}


def test_ctrl_shift_v_with_no_look_picked_up_stays_the_browsers(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    # No look to lay: the browser's paste of plain words.
    assert not stopped(page, "Control+Shift+V")
    assert stopped(page, "Control+Shift+C")
    # Once a look is picked up, the key lays it.
    assert stopped(page, "Control+Shift+V")


def test_a_brush_drag_with_ctrl_in_an_open_text_makes_no_copy_of_the_block(editor):
    """#756: Moveable hears of the press before the editor does; with Ctrl it would leave a copy."""
    client = user()
    page = editor(box("a", "text", {**TEXT, "text": "Der Hund ist braun und klein"}), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    w = word(page, "a", "Hund")
    page.mouse.dblclick((w["x"] + w["right"]) / 2, w["y"])
    page.keyboard.press("Control+b")
    x = saved_x(page, client)
    brush(page).click()
    expect_brush(page, True)
    w = word(page, "a", "braun")
    page.keyboard.down("Control")
    page.mouse.move(w["x"] + 1, w["y"])
    page.mouse.down()
    page.mouse.move(w["right"] - 1, w["y"], steps=5)
    page.mouse.up()
    page.keyboard.up("Control")
    expect(page.locator(".block")).to_have_count(1)
    assert [b["id"] for b in saved(page, client)] == ["a"]
    assert saved_x(page, client) == x
