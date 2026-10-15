"""A Selbstkontrolle block links maths blocks of the sheet. The link, the grow, the variants, the
copy and the letter boxes hold as the contract of #89 says (frontend/src/selbstkontrolle.ts).

The expected numbers are written here by hand. Nothing reads them from the code under test.
"""

from playwright.sync_api import expect
from ui import at, box, doc, maths, pick, reload, sheet, user

SK = {
    "form": "mixed",
    "links": ["m"],
    "word": "",
    "title": "Selbstkontrolle",
    "size": 14,
    "turn": "none",
    "seed": 5,
}
UHR = {
    "numbers": "all",
    "minutes": True,
    "ring": False,
    "task": "read",
    "answer": "box",
    "format": "12",
    "region": "nach",
    "count": 4,
    "cols": 4,
    "step": 15,
    "fill": "free",
    "times": [210, 585, 720, 370],
    "seed": 3,
}
DREI = {"count": 4, "columns": 4, "max": 20, "given": "inner", "empty": False, "seed": 7}


def sk(props=SK, z=2, **more):
    """A Selbstkontrolle block, 180 mm wide and 30 mm high unless `more` says otherwise."""
    return box("s", "selbstkontrolle", props, z=z, **{"w": 180, "h": 30, **more})


def maths_block(client):
    """A maths block of 12 sums: 12 results for the Selbstkontrolle to take."""
    return box("m", "maths", maths(client, count=12, max=100), z=1)


def stored(page, client):
    """The blocks of the first page as the server holds them, by name."""
    return {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}


def panel_tick(page, label):
    """The panel's checkbox for the maths block that the label names."""
    return page.locator(".panel label", has_text=label).locator("input[type=checkbox]")


def test_ticking_a_block_grows_the_selbstkontrolle_and_one_undo_takes_both_back(editor):
    """Grow rule: a 12 mm block linked to nothing grows when a 12 result block is ticked; one
    Control+z takes the link and the height back together."""
    client = user()
    page = editor(maths_block(client), sk(SK | {"links": []}, h=12), client=client)
    pick(page, "s")
    panel_tick(page, "Rechnen").check()
    grown = stored(page, client)["s"]
    assert grown["props"]["links"] == ["m"]
    assert grown["h"] > 12
    # The key reaches the sheet only when the focus is off the panel's checkbox.
    page.evaluate("document.activeElement.blur()")
    with page.expect_response(lambda r: r.request.method in ("PUT", "PATCH")) as saving:
        page.keyboard.press("Control+z")
    saving.value.finished()
    back = stored(page, client)["s"]
    assert back["props"]["links"] == []
    assert back["h"] == 12


def test_twelve_results_in_12_mm_never_spill_out_of_the_block(editor):
    """The text shrinks to fit: 12 results in a 180 by 12 mm block leave no part below the block."""
    client = user()
    page = editor(maths_block(client), sk(h=12), client=client)
    handle = at(page, "s").locator(".selbstkontrolle").element_handle()
    page.wait_for_function("el => el.scrollHeight <= el.clientHeight + 1", arg=handle)


def test_a_variant_gives_the_selbstkontrolle_another_seed_and_keeps_its_form_links_and_word():
    """Variants, server: variant B has the Selbstkontrolle with seed 5 changed, form, links and
    word as stored."""
    client = user()
    word = "A" * 12
    s = sheet(
        client,
        [maths_block(client), sk({**SK, "form": "word", "word": word})],
    )
    answer = client.get(f"/api/sheets/{s['id']}/variante/B").json()["doc"]
    block = {b["id"]: b for b in answer["pages"][0]["blocks"]}["s"]
    assert block["props"]["seed"] != 5
    assert block["props"]["form"] == "word"
    assert block["props"]["links"] == ["m"]
    assert block["props"]["word"] == word


def test_a_word_that_variant_b_cannot_fill_is_named_in_the_dialog(editor):
    """Variants dialog: 12 stored tasks and a 12 letter word fill the stored sheet. B is answered
    with one task less, so its word has 12 letters for 11 tasks and the dialog names the block."""
    client = user()
    word = "A" * 12
    page = editor(
        maths_block(client),
        sk({**SK, "form": "word", "word": word}, h=30),
        client=client,
    )
    expect(at(page, "s").locator(".hint")).to_have_count(0)

    def one_task_less(route):
        answer = route.fetch().json()
        for block in answer["doc"]["pages"][0]["blocks"]:
            if block["type"] == "maths":
                block["props"]["exercises"] = block["props"]["exercises"][:-1]
        route.fulfill(json=answer)

    page.route("**/api/sheets/*/variante/B", one_task_less)
    page.get_by_role("tab", name="Ansicht").click()
    page.locator(".panel").get_by_role("button", name="Varianten drucken", exact=True).click()
    expect(page.get_by_role("dialog")).to_be_visible()
    expect(page.get_by_role("alert")).to_contain_text("Selbstkontrolle-Block auf Seite 1")


def test_copy_paste_and_ctrl_d_keep_the_links_and_delete_undo_brings_them_back(editor):
    """Copy and paste keep the links; Ctrl+D doubles the block; delete then undo gives it back
    with its links."""
    client = user()
    page = editor(maths_block(client), sk(), client=client)
    pick(page, "s")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    copies = [b for b in stored(page, client).values() if b["type"] == "selbstkontrolle"]
    assert len(copies) == 2
    assert all(b["props"]["links"] == ["m"] for b in copies)
    page.keyboard.press("Control+d")
    expect(page.locator(".block[data-id]")).to_have_count(4)
    page.keyboard.press("Delete")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    page.keyboard.press("Control+z")
    expect(page.locator(".block[data-id]")).to_have_count(4)
    blocks = [b for b in stored(page, client).values() if b["type"] == "selbstkontrolle"]
    assert len(blocks) == 3
    assert all(b["props"]["links"] == ["m"] for b in blocks)


def test_an_older_build_keeps_the_selbstkontrolle_props_through_a_save_and_a_reload(editor):
    """A save leaves the stored props exactly as they were, through a reload too."""
    client = user()
    page = editor(maths_block(client), sk(), client=client)
    pick(page, "m")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(page, client)["s"]["props"] == SK
    reload(page, page.url)
    expect(at(page, "s")).to_be_visible()
    assert stored(page, client)["s"]["props"] == SK


def test_rechendreieck_and_uhr_draw_one_letter_box_per_task_in_word_form(editor):
    """Letter boxes: a Rechendreieck with 4 triangles and an Uhr with 4 clocks, both linked to a
    word Selbstkontrolle, draw 4 boxes each."""
    client = user()
    page = editor(
        box("d", "rechendreieck", DREI, w=180, h=50, y=20, z=1),
        box("u", "uhr", UHR, w=180, h=110, y=100, z=2),
        sk({**SK, "form": "word", "word": "ABCDEFGH", "links": ["d", "u"]}, y=230, z=3),
        client=client,
    )
    expect(at(page, "d").locator(".letter")).to_have_count(4)
    expect(at(page, "u").locator(".letter")).to_have_count(4)


def test_a_clock_with_task_draw_draws_no_letter_and_adds_no_task(editor):
    """An Uhr with task "draw" has no task: no letter box, and the word's 4 letters meet 0 tasks."""
    client = user()
    page = editor(
        box("u", "uhr", {**UHR, "task": "draw"}, w=180, h=110, y=20, z=1),
        sk({**SK, "form": "word", "word": "ABCD", "links": ["u"]}, y=150, z=2),
        client=client,
    )
    expect(at(page, "u").locator(".letter")).to_have_count(0)
    expect(at(page, "s").locator(".hint")).to_contain_text("die Aufgaben sind 0")


def test_a_lost_link_shows_its_line_in_the_editor(editor):
    """Extra: a link to a block that is gone shows the line that says the source is lost."""
    client = user()
    page = editor(sk({**SK, "links": ["gone"]}), client=client)
    expect(at(page, "s")).to_contain_text("Die Selbstkontrolle hat ihre Quelle verloren.")


def test_the_drucken_choice_turns_the_block_and_the_store_keeps_it(editor):
    """Extra: "Drucken" set to "Auf dem Kopf" stores turn "upside" and the block shows it turned."""
    client = user()
    page = editor(maths_block(client), sk(), client=client)
    pick(page, "s")
    page.locator(".panel").get_by_label("Drucken", exact=True).select_option("upside")
    expect(at(page, "s").locator(".selbstkontrolle")).to_have_class("selbstkontrolle upside")
    assert stored(page, client)["s"]["props"]["turn"] == "upside"


def test_seite_duplizieren_links_the_copied_selbstkontrolle_to_the_copied_block(editor):
    """Review B: on the copied page the Selbstkontrolle links the copied Rechnen, not page 1's."""
    from test_menu import right_thumb, run

    client = user()
    page = editor(
        maths_block(client), sk({**SK, "form": "word", "word": "A" * 12}), client=client, theme=""
    )
    right_thumb(page, 0)
    run(page, "Seite duplizieren")
    expect(page.locator(".sheet[data-page]")).to_have_count(2)
    second = doc(page, client)["pages"][1]["blocks"]
    [copy] = [b for b in second if b["type"] == "selbstkontrolle"]
    [rechnen] = [b for b in second if b["type"] == "maths"]
    assert copy["props"]["links"] == [rechnen["id"]]
    expect(page.locator('.sheet[data-page="1"] .maths .letter')).to_have_count(12)


def test_copy_and_paste_of_both_links_the_pasted_block(editor):
    """Review B: both copied and pasted: the pasted Selbstkontrolle links the pasted Rechnen."""
    client = user()
    page = editor(maths_block(client), sk(), client=client)
    pick(page, "m")
    page.keyboard.press("Control+a")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(4)
    blocks = stored(page, client)
    [new] = [b for b in blocks.values() if b["type"] == "selbstkontrolle" and b["id"] != "s"]
    [pasted] = [b for b in blocks.values() if b["type"] == "maths" and b["id"] != "m"]
    assert new["props"]["links"] == [pasted["id"]]
    assert blocks["s"]["props"]["links"] == ["m"]


def test_a_long_word_table_shrinks_to_the_width_and_is_not_cut(editor):
    """Review B: 16 different results and a 16 letter word at 20 pt fit the block's width."""
    client = user()
    sixteen = [{"op": "+", "a": n, "b": 10, "result": n + 10, "rest": 0} for n in range(16)]
    page = editor(
        box("m", "maths", maths(client, exercises=sixteen, count=16), z=1, h=40),
        sk({**SK, "form": "word", "word": "ABCDEFGHIJKLMNOP", "size": 20}, h=40, y=150),
        client=client,
    )
    table = at(page, "s").locator("table.word")
    expect(table.locator("tr.letters td")).to_have_count(16)
    inner = at(page, "s").locator(".selbstkontrolle")
    assert inner.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
    right = table.evaluate("t => t.getBoundingClientRect().right")
    assert right <= inner.evaluate("e => e.getBoundingClientRect().right") + 1


def test_a_grown_block_shows_its_type_at_its_own_size(editor):
    """Review A: linking 12 results grows the block so far that the type needs no shrinking."""
    client = user()
    page = editor(maths_block(client), sk(SK | {"links": []}, h=12, y=150), client=client)
    pick(page, "s")
    panel_tick(page, "Rechnen").check()
    assert stored(page, client)["s"]["h"] > 12
    page.evaluate("document.activeElement.blur()")
    expect(at(page, "s").locator("ul.mixed li")).to_have_count(12)
    fit = (
        at(page, "s").locator(".selbstkontrolle").evaluate("e => e.style.getPropertyValue('--fit')")
    )
    assert fit == "" or float(fit) > 0.97, fit
