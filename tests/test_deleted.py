"""A sheet deleted on another device says so at the next save, and nothing is dropped unasked
(issue #360).

The teacher keeps what is on screen and chooses: `Als neues Blatt behalten` or `Verwerfen`. The
choice stands in the open editor as a banner, and as a line above the page wherever the sheet's
editor is not there: on the list, at the app's start, and on the dead sheet's own address. Until
the teacher chose, the browser's record stays and the dead sheet takes no save.

Built on test_saves.py: the sheet A, its gate, and a clock that stands. The delete is the
server's own, through the test's client, so each 404 names the owner as the server does.

The docstrings name the lines of the checklist.
"""

# The fixtures `window` and `run` are imported, and each test names one as its argument.
# ruff: noqa: F811

import re

from playwright.sync_api import expect
from test_loading import READY, window  # noqa: F401
from test_saves import (  # noqa: F401
    ASKS,
    LEFT,
    NOTICE,
    again,
    answer,
    change,
    kept_x,
    leave,
    nudge,
    record,
    run,
    shut,
    start,
)
from test_signed_out import login
from test_stale import STATUS, TURNS
from ui import at, reload, unpick

KEEP, DROP = "Als neues Blatt behalten", "Verwerfen"
SAYS = "Dieses Blatt wurde auf einem anderen Gerät gelöscht. Was du hier siehst, ist noch da."
LINE = "„a“ wurde auf einem anderen Gerät gelöscht. Deine letzte Änderung ist noch da."
BUSY = "Lädt …"
WORD = "Das hat nicht geklappt. Prüfe deine Verbindung und versuche es noch einmal."
PDF_GONE = (
    "Das PDF konnte nicht erstellt werden. Dieses Blatt wurde auf einem anderen Gerät gelöscht. "
    "Wähle „Als neues Blatt behalten“, dann gibt es wieder ein PDF."
)
# A record as the app wrote it before it kept the sheet's name.
OLD = """for (const k of Object.keys(localStorage)) {
    if (!k.startsWith('unsaved:')) continue;
    const kept = JSON.parse(localStorage[k]);
    delete kept.name;
    localStorage[k] = JSON.stringify(kept);
}"""


def makes(request):
    """Whether a request makes a new sheet."""
    return request.method == "POST" and request.url.endswith("/api/sheets")


def press(told, name):
    """Presses a choice of the banner or the line. `Verwerfen` asks once more, and the teacher
    says yes: to that one question, for the browser's own, at a reload or as the tab shuts, is
    not this one's to answer."""
    if name == DROP:
        told.page.once("dialog", lambda dialog: dialog.accept())
    told.get_by_role("button", name=name).click()


def delete(run):
    """Another device deletes A."""
    assert run.client.delete(f"/api/sheets/{run.ids['a']}").status_code == 200


def deleted(run):
    """A is open and changed, another device deletes it, and the save finds it so. Gives the
    page, A's gate and where the block shows."""
    page, gate = start(run)
    change(run)
    moved = at(page, "a").evaluate(LEFT)
    delete(run)
    answer(run, "a")
    return page, gate, moved


def left(run):
    """The teacher changed A and went on to the list at once, another device deleted A, and the
    save finds it so with no editor there."""
    page, _ = leave(run, "held", "list")
    delete(run)
    with page.expect_response(f"{run.server}/api/sheets") as listed:
        answer(run, "a")
    listed.value.finished()
    return page


def expect_choice(told, says):
    """The banner or the line says so, as an alert, with both choices to press."""
    expect(told).to_have_text(re.compile(re.escape(says)))
    expect(told).to_have_attribute("role", "alert")
    for name in (KEEP, DROP):
        expect(told.get_by_role("button", name=name)).to_be_enabled()
    expect(told).not_to_contain_text(BUSY)


def expect_new(run, page, x=16, title="a"):
    """The new sheet is open and saved, with the page as it stood, and A's record is gone. Gives
    the new sheet."""
    a = run.ids["a"]
    expect(page).not_to_have_url(re.compile(rf"/blatt/{a}$"))
    expect(page).to_have_url(re.compile(r"/blatt/\d+$"))
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    expect(page.locator(".clash, .notice")).to_have_count(0)
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(at(page, "a")).to_contain_text("Blatt A")
    new = run.client.get(f"/api/sheets/{page.url.rsplit('/', 1)[1]}").json()
    assert new["doc"]["pages"][0]["blocks"][0]["x"] == x
    assert new["title"] == title
    assert record(page, a) is None
    return new


def expect_list(page, rows=2):
    expect(page.get_by_role("heading", name="Meine Blätter")).to_be_visible()
    expect(page.locator(".sheets li")).to_have_count(rows)
    expect(page.locator(NOTICE)).to_have_count(0)


def test_a_save_that_finds_its_sheet_deleted_says_so_and_the_page_stays_as_typed(run):
    """A1, and I2: the banner is an alert."""
    page, _, moved = deleted(run)
    expect_choice(page.locator(".clash"), SAYS)
    expect(page.get_by_role("alert")).to_have_count(1)
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    expect(page.get_by_role("heading", name="Blatt nicht gefunden")).to_have_count(0)
    assert kept_x(page, run) == 16


def test_a_tab_that_was_offline_at_the_delete_says_so_once_it_is_back(run):
    """A2: the save fails with no connection, the sheet is deleted meanwhile, and the next try
    finds it so."""
    page, gate = start(run)
    gate.keep = False
    page.context.set_offline(True)
    with page.expect_event("requestfailed", gate.asks("PATCH")):
        nudge(run)
        page.clock.run_for(2000)
    page.evaluate(TURNS)
    moved = at(page, "a").evaluate(LEFT)
    expect(page.locator(".clash")).to_have_count(0)
    delete(run)
    with page.expect_response(gate.answers("PATCH")) as got:
        page.context.set_offline(False)
        # The browser says that it is back, or the try's own clock runs out.
        page.clock.run_for(2000)
    assert got.value.status == 404
    expect_choice(page.locator(".clash"), SAYS)
    expect(at(page, "a")).to_have_css("left", moved)
    assert kept_x(page, run) == 16


def test_nothing_is_dropped_or_sent_until_the_teacher_chose(run):
    """A3: the record stays through minutes, a reload and a login, the dead sheet takes no
    further save, and the window asks before it shuts."""
    page, gate, _ = deleted(run)
    a = run.ids["a"]
    kept = record(page, a)
    gate.keep = False
    page.evaluate("dispatchEvent(new Event('online'))")
    page.clock.run_for(300000)
    page.evaluate(TURNS)
    assert len(run.sent) == 1
    assert record(page, a) == kept
    page.clock.resume()
    page.reload()
    expect_choice(page.locator(NOTICE), LINE)
    assert record(page, a) == kept
    # The session runs out, and the teacher signs in again.
    page.context.clear_cookies()
    page.reload()
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    assert record(page, a) == kept
    login(page, run.server, run.client)
    expect_choice(page.locator(NOTICE), LINE)
    assert record(page, a) == kept
    assert len(run.sent) == 1
    assert shut(page) == ASKS
    assert run.client.get(f"/api/sheets/{a}").status_code == 404


def test_keeping_as_a_new_sheet_takes_the_title_and_the_page_and_opens_it(run):
    """A4: with no connection it says so and the choice stands; the second try makes the sheet."""
    page, _, _ = deleted(run)
    page.get_by_label("Titel", exact=True).fill("Neu")
    banner = page.locator(".clash")
    page.context.set_offline(True)
    banner.get_by_role("button", name=KEEP).click()
    expect(banner).to_contain_text(WORD)
    expect_choice(banner, SAYS)
    assert kept_x(page, run) == 16
    assert len(run.client.get("/api/sheets").json()) == 2
    page.context.set_offline(False)
    banner.get_by_role("button", name=KEEP).click()
    expect_new(run, page, title="Neu")
    assert len(run.client.get("/api/sheets").json()) == 3
    assert len(run.sent) == 1


def test_dropping_takes_the_change_and_its_record_and_shows_the_list(run):
    """A5"""
    page, _, _ = deleted(run)
    press(page.locator(".clash"), DROP)
    expect_list(page)
    assert record(page, run.ids["a"]) is None
    assert shut(page) == []
    assert len(run.client.get("/api/sheets").json()) == 2


def test_a_choice_under_way_takes_no_second_press(run):
    """I1: two presses before the first is answered make one sheet."""
    page, _, _ = deleted(run)
    held = []
    page.route(
        f"{run.server}/api/sheets",
        lambda route: held.append(route) if route.request.method == "POST" else route.continue_(),
    )
    banner = page.locator(".clash")
    press = banner.get_by_role("button", name=KEEP)
    with page.expect_request(makes):
        press.evaluate("el => { el.click(); el.click(); }")
    page.evaluate(TURNS)
    expect(banner).to_contain_text(BUSY)
    for name in (KEEP, DROP):
        expect(banner.get_by_role("button", name=name)).to_be_disabled()
    assert len(held) == 1
    held.pop().continue_()
    expect_new(run, page)
    assert not held
    assert len(run.client.get("/api/sheets").json()) == 3


def test_a_change_made_while_the_new_sheet_is_made_goes_into_it(run):
    """I3: the new sheet takes the page as it stood at the press, and its saver sends what the
    teacher changed until the server answered."""
    page, _, _ = deleted(run)
    held = []
    page.route(
        f"{run.server}/api/sheets",
        lambda route: held.append(route) if route.request.method == "POST" else route.continue_(),
    )
    with page.expect_request(makes) as made:
        page.locator(".clash").get_by_role("button", name=KEEP).click()
    assert made.value.post_data_json["doc"]["pages"][0]["blocks"][0]["x"] == 16
    unpick(page)
    nudge(run)
    held.pop().continue_()
    expect_new(run, page, x=17)
    assert len(run.client.get("/api/sheets").json()) == 3


def test_a_keep_whose_answer_never_came_makes_no_second_sheet_on_the_next_press(run):
    """4: the new sheet was made and its answer never came. The next press finds that sheet and
    makes no second one."""
    page, _, _ = deleted(run)
    page.route(
        f"{run.server}/api/sheets",
        lambda route: route.fetch() if route.request.method == "POST" else route.continue_(),
    )
    banner = page.locator(".clash")
    with page.expect_request(makes):
        banner.get_by_role("button", name=KEEP).click()
    page.clock.run_for(20000)
    expect(banner).to_contain_text(WORD)
    banner.get_by_role("button", name=KEEP).click()
    expect_new(run, page)
    assert len(run.client.get("/api/sheets").json()) == 3


def test_a_second_press_finds_the_sheet_made_and_takes_the_newer_change(run):
    """4, follow-up A: the first press's sheet is found, not made again, and it takes the change
    made since the first press."""
    page, _, _ = deleted(run)
    page.route(
        f"{run.server}/api/sheets",
        lambda route: route.fetch() if route.request.method == "POST" else route.continue_(),
    )
    banner = page.locator(".clash")
    with page.expect_request(makes):
        banner.get_by_role("button", name=KEEP).click()
    page.clock.run_for(20000)
    expect(banner).to_contain_text(WORD)
    unpick(page)
    nudge(run)
    banner.get_by_role("button", name=KEEP).click()
    expect_new(run, page, x=17)
    assert len(run.client.get("/api/sheets").json()) == 3


def test_a_keep_asked_before_a_reload_finds_the_sheet_made_and_makes_no_second(run):
    """4, follow-up B: the press's answer never came and the page reloaded. The next press, on the
    reloaded page, finds the sheet made and makes no second one."""
    page, _, _ = deleted(run)
    a = run.ids["a"]
    page.route(
        f"{run.server}/api/sheets",
        lambda route: route.fetch() if route.request.method == "POST" else route.continue_(),
    )
    with page.expect_request(makes):
        page.locator(".clash").get_by_role("button", name=KEEP).click()
    page.clock.resume()
    reload(page, f"{run.server}/blatt/{a}")
    line = page.locator(NOTICE)
    expect_choice(line, LINE)
    press(line, KEEP)
    expect_new(run, page)
    assert len(run.client.get("/api/sheets").json()) == 3


def tab_to(page, press):
    for _ in range(40):
        page.keyboard.press("Tab")
        if press.evaluate("el => el === document.activeElement"):
            break
    expect(press).to_be_focused()


def test_the_banners_buttons_are_reached_by_tab_and_pressed_by_enter(run):
    """I2"""
    page, _, _ = deleted(run)
    banner = page.locator(".clash")
    expect_choice(banner, SAYS)
    page.get_by_label("Titel", exact=True).focus()
    tab_to(page, banner.get_by_role("button", name=KEEP))
    page.keyboard.press("Tab")
    expect(banner.get_by_role("button", name=DROP)).to_be_focused()
    page.once("dialog", lambda dialog: dialog.accept())
    page.keyboard.press("Enter")
    expect_list(page)


def test_the_editor_works_on_under_the_banner_and_the_page_is_kept_as_it_stands_then(run):
    """I3: a change, undo and redo, and a new title. Undone back to what the server held last,
    the page is still kept: the server holds nothing of it."""
    page, _, _ = deleted(run)
    a = run.ids["a"]
    banner = page.locator(".clash")
    unpick(page)
    nudge(run)
    page.clock.run_for(1000)
    page.evaluate(TURNS)
    assert kept_x(page, run) == 17
    for x in (16, 15):
        page.get_by_role("button", name="Rückgängig").click()
        page.clock.run_for(1000)
        page.evaluate(TURNS)
        assert kept_x(page, run) == x
    expect_choice(banner, SAYS)
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    for _ in range(2):
        page.get_by_role("button", name="Wiederholen").click()
    page.get_by_label("Titel", exact=True).fill("Getippt")
    page.evaluate(TURNS)
    assert len(run.sent) == 1
    banner.get_by_role("button", name=KEEP).click()
    expect_new(run, page, x=17, title="Getippt")
    assert run.client.get(f"/api/sheets/{a}").status_code == 404
