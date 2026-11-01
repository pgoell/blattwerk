"""A change the server never got stays in the browser and is saved on the next visit."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import json
import re
from contextlib import ExitStack

import pytest
from playwright.sync_api import expect
from test_loading import (
    READY,
    expect_ready,
    window,  # noqa: F401
)
from test_saves import (
    ASKS,
    LEFT,
    NOTICE,
    again,
    answer,
    asks_me,
    change,
    down,
    leave,
    let_go,
    nudge,
    record,
    run,  # noqa: F401
    shut,
    stalled,
    start,
    to_list,
    unsaved,
    x_of,
)
from test_stale import (
    KEPT,
    STATUS,
    TURNS,
    blocks,
    named,
)
from ui import (
    PASSWORD,
    TEXT,
    at,
    box,
    reload,
    user,
)


@pytest.mark.parametrize("arrived", [False, True], ids=["save-never-arrived", "save-arrived"])
def test_a_tab_shut_with_a_save_under_way_keeps_the_newer_change_for_the_next_visit(run, arrived):
    """A6, I3: the change behind the save under way is not sent beside it. The browser keeps it,
    and the next visit shows and saves it, whether the save under way arrived or not."""
    page, gate = start(run)
    with ExitStack() as server:
        if arrived:
            change(run)
            assert gate.saves.pop().fetch().status == 200
        else:
            came = server.enter_context(stalled())
            gate.keep = False
            change(run)
            assert came.acquire(timeout=5)
        nudge(run)
        moved = at(page, "a").evaluate(LEFT)
        asked = shut(page, gates=arrived)
    assert asked == ASKS
    assert [run.whose(request) for request in run.sent] == ["a"]
    assert x_of(run, "a") == (16 if arrived else 15)
    page, gate, sent = again(run, keep=True)
    expect_ready(page, 1)
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Speichert …")
    assert let_go(page, gate).status == 200
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(page.locator(".clash")).to_have_count(0)
    assert x_of(run, "a") == 17
    assert record(page, run.ids["a"]) is None
    assert len(sent) == 1


def test_a_save_that_fails_as_the_tab_shuts_does_not_send_the_newer_change(run):
    """#467: the save under way is answered 503 once the tab has started to shut. pagehide then
    sends nothing of the newer change. The browser keeps it."""
    page, gate = start(run)
    change(run)
    nudge(run)
    page.evaluate("dispatchEvent(new Event('beforeunload'))")
    answer(run, "a", 503)
    page.evaluate(TURNS)
    page.evaluate("dispatchEvent(new PageTransitionEvent('pagehide', {persisted: false}))")
    page.evaluate(TURNS)
    assert record(page, run.ids["a"])["doc"]["pages"][0]["blocks"][0]["x"] == 17
    assert not gate.saves
    assert x_of(run, "a") == 15


def test_a_save_the_browser_drops_as_the_tab_shuts_does_not_send_the_newer_change(run):
    """#390: WebKit once aborted the save under way before the tab had shut, and the next visit
    read Gespeichert. The newer change stays for that visit and is not sent beside the first."""
    page, gate = start(run)
    change(run)
    nudge(run)
    moved = at(page, "a").evaluate(LEFT)
    # The browser drops the save it was still sending, as it can when the tab goes.
    gate.saves.pop().abort()
    page.evaluate(TURNS)
    assert not gate.saves
    assert shut(page, gates=True) == ASKS
    assert not gate.saves
    assert x_of(run, "a") == 15
    page, gate, sent = again(run, keep=True)
    expect_ready(page, 1)
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Speichert …")
    assert let_go(page, gate).status == 200
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(page.locator(".clash")).to_have_count(0)
    assert x_of(run, "a") == 17
    assert record(page, run.ids["a"]) is None
    assert len(sent) == 1


@pytest.mark.parametrize("how", ["reload", "shut"])
def test_a_change_whose_save_failed_is_saved_on_the_next_visit(run, how):
    """A7"""
    page, gate = start(run)
    change(run)
    answer(run, "a", 500)
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    moved = at(page, "a").evaluate(LEFT)
    assert record(page, run.ids["a"])["base"] == 1
    # The tab tries once more as it goes, and the next visit tries at once: both in vain.
    gate.keep = False
    with down(2):
        if how == "reload":
            page.clock.resume()
            page.reload()
        else:
            shut(page)
            page, gate, _ = again(run)
        expect_ready(page, 1)
        expect(at(page, "a")).to_have_css("left", moved)
        expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
        assert x_of(run, "a") == 15
    # The server is back.
    with page.expect_response(lambda r: gate.answers("PATCH")(r) and r.ok) as saved:
        page.evaluate("dispatchEvent(new Event('online'))")
    saved.value.finished()
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    assert x_of(run, "a") == 16
    assert record(page, run.ids["a"]) is None


def test_a_large_sheets_last_change_is_saved_on_the_next_visit(run):
    """A7: the browser sends no save over 64 KiB from a tab that shuts."""
    was = run.held("a")
    heavy = [box(f"x{n}", "text", {**TEXT, "text": "schwer " * 20}) for n in range(300)]
    doc = {**was["doc"], "pages": [*was["doc"]["pages"], {"blocks": heavy}]}
    assert len(json.dumps(doc)) > 64 * 1024
    large = {"doc": doc, "version": was["version"]}
    assert run.client.patch(f"/api/sheets/{run.ids['a']}", json=large).status_code == 200
    page, gate = start(run)
    page.evaluate(KEPT)
    nudge(run)
    moved = at(page, "a").evaluate(LEFT)
    assert page.evaluate("window.kept") == []
    # Whether that save leaves the tab at all is the browser's to say: the server is down until
    # the next visit stands, so it is surely not what saves the change.
    with down():
        shut(page)
        page, gate, _ = again(run, keep=True)
        expect_ready(page, 301)
        expect(at(page, "a")).to_have_css("left", moved)
        expect(page.locator(STATUS)).to_have_text("Speichert …")
        assert x_of(run, "a") == 15
    assert let_go(page, gate).status == 200
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    assert x_of(run, "a") == 16
    assert record(page, run.ids["a"]) is None


@pytest.mark.parametrize("choice", ["Andere Version laden", "Mit dieser überschreiben"])
def test_a_kept_change_of_a_sheet_changed_elsewhere_asks_which_version_stays(run, choice):
    """I1: nothing is overwritten unasked."""
    page, _ = start(run)
    nudge(run)
    moved = at(page, "a").evaluate(LEFT)
    shut(page, 1)
    # Another device moves the block far to the right meanwhile.
    was = run.held("a")
    was["doc"]["pages"][0]["blocks"][0]["x"] = 40
    other = {"doc": was["doc"], "version": was["version"]}
    assert run.client.patch(f"/api/sheets/{run.ids['a']}", json=other).status_code == 200
    page, _, sent = again(run)
    expect_ready(page, 1)
    banner = page.locator(".clash")
    expect(banner).to_contain_text(
        "Dieses Blatt wurde in einem anderen Fenster oder auf einem anderen Gerät geändert."
    )
    for name in ("Andere Version laden", "Mit dieser überschreiben"):
        expect(banner.get_by_role("button", name=name)).to_be_visible()
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    page.evaluate(TURNS)
    assert not sent
    assert x_of(run, "a") == 40
    assert record(page, run.ids["a"])["doc"]["pages"][0]["blocks"][0]["x"] == 16
    banner.get_by_role("button", name=choice).click()
    expect(banner).to_have_count(0)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    if choice == "Andere Version laden":
        expect(at(page, "a")).not_to_have_css("left", moved)
        assert not sent
    else:
        expect(at(page, "a")).to_have_css("left", moved)
    assert x_of(run, "a") == (40 if choice == "Andere Version laden" else 16)
    assert record(page, run.ids["a"]) is None


def test_a_kept_change_belongs_to_its_account(run):
    """I2: another account in the same browser neither sees nor saves it, and its owner still
    gets it later."""
    page, _ = start(run)
    nudge(run)
    moved = at(page, "a").evaluate(LEFT)
    shut(page, 1)
    a = run.ids["a"]
    other = user()
    d = named(other, "d")
    run.ids["d"] = d
    # The owner's sheet is not there for the other account.
    page, _, sent = again(run, client=other)
    expect(page.get_by_role("heading", name="Blatt nicht gefunden")).to_be_visible()
    kept = record(page, a)
    assert kept["doc"]["pages"][0]["blocks"][0]["x"] == 16
    # Nor does the record show on a sheet of the other account, should it lie under that one's id.
    page.evaluate(f"localStorage.setItem('unsaved:{d}', localStorage.getItem('unsaved:{a}'))")
    page.close()
    page, _, sent = again(run, "d")
    expect_ready(page, 1)
    expect(at(page, "d")).to_contain_text("Blatt D")
    expect(at(page, "a")).to_have_count(0)
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(page.locator(".clash, .notice")).to_have_count(0)
    page.evaluate(TURNS)
    assert not sent
    assert record(page, a) == kept
    assert record(page, d) == kept
    assert blocks(other.get(f"/api/sheets/{d}").json()["doc"]) == [("d", "Blatt D")]
    assert x_of(run, "a") == 15
    page.close()
    # The owner comes back.
    page, _, sent = again(run, client=run.client)
    expect_ready(page, 1)
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    assert x_of(run, "a") == 16
    assert record(page, a) is None


def test_a_changed_title_is_kept_and_tried_again_like_a_changed_sheet(run):
    """I4"""
    page, gate = start(run)
    page.get_by_label("Titel", exact=True).fill("Neu")
    page.evaluate(TURNS)
    for how in (500, "cut"):
        with page.expect_request(gate.asks("PATCH")) as sent:
            page.clock.run_for(2000)
        assert sent.value.post_data_json["title"] == "Neu"
        page.evaluate(TURNS)
        answer(run, "a", how)
        expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    assert record(page, run.ids["a"])["title"] == "Neu"
    assert run.held("a")["title"] == "a"
    page.clock.resume()
    gate.keep = False
    with down(2):
        page.reload()
        expect_ready(page, 1)
        expect(page.get_by_label("Titel", exact=True)).to_have_value("Neu")
        expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    with page.expect_response(lambda r: gate.answers("PATCH")(r) and r.ok) as saved:
        page.evaluate("dispatchEvent(new Event('online'))")
    assert saved.value.request.post_data_json["title"] == "Neu"
    saved.value.finished()
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    assert run.held("a")["title"] == "Neu"
    assert record(page, run.ids["a"]) is None


def test_the_browser_asks_before_the_tab_shuts_while_a_change_is_unsaved(run):
    """A9"""
    page, _ = start(run)
    nudge(run)
    assert shut(page, 1) == ASKS


def test_the_browser_does_not_ask_when_all_is_saved(run):
    """A9"""
    page, gate = start(run)
    gate.keep = False
    with page.expect_response(gate.answers("PATCH")) as saved:
        nudge(run)
        page.clock.run_for(2000)
    saved.value.finished()
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    assert shut(page) == []
    assert x_of(run, "a") == 16


def test_a_sheet_deleted_meanwhile_keeps_its_change_and_its_notice_asks_what_becomes_of_it(run):
    """I5, and #353 A5: the 404 names its owner, and nobody is asked who is signed in. #360: the
    change is not dropped; the notice says that the sheet was deleted, and the teacher chooses."""
    page, gate = leave(run, "held", "sheet")
    page.clock.run_for(1000)
    expect(page.locator(NOTICE)).to_have_text(unsaved("a"))
    kept = record(page, run.ids["a"])
    assert kept
    assert run.client.delete(f"/api/sheets/{run.ids['a']}").status_code == 200
    asked = asks_me(page)
    answer(run, "a")
    said = page.locator(NOTICE)
    expect(said).to_contain_text(
        "„a“ wurde auf einem anderen Gerät gelöscht. Deine letzte Änderung ist noch da."
    )
    assert record(page, run.ids["a"]) == kept
    assert asked == []
    # Nothing more is tried, and the app goes on.
    page.clock.run_for(60000)
    page.evaluate(TURNS)
    assert not gate.saves
    assert [run.whose(request) for request in run.sent] == ["a"]
    run.check()
    to_list(run)
    expect(page.locator(".sheets li")).to_have_count(2)
    expect(said).to_have_count(1)
    assert record(page, run.ids["a"]) == kept
    said.page.once("dialog", lambda dialog: dialog.accept())
    said.get_by_role("button", name="Verwerfen").click()
    expect(said).to_have_count(0)
    assert record(page, run.ids["a"]) is None
    expect(page.locator(".sheets li")).to_have_count(2)


def test_pdf_goes_on_once_a_save_that_never_answers_is_given_up(run):
    """I6"""
    page, gate = start(run)
    nudge(run)
    got, asked = [], []
    page.on("download", lambda download: got.append(download))
    page.on("dialog", lambda dialog: (asked.append(dialog.type), dialog.accept()))
    with page.expect_request(gate.asks("PATCH")):
        page.get_by_role("button", name="PDF", exact=True).click()
    page.evaluate(TURNS)
    gate.saves.pop()
    page.clock.run_for(19999)
    page.evaluate(TURNS)
    assert not got
    with page.expect_download(timeout=20000) as download:
        page.clock.run_for(1)
    assert download.value.suggested_filename == "a.pdf"
    # A download leaves the page where it is: the browser has nothing to ask.
    assert asked == []
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")


def test_the_list_shows_a_sheet_as_it_was_left_once_its_late_save_lands(run):
    """I7"""
    page, gate = start(run)
    page.get_by_label("Titel", exact=True).fill("Neu")
    page.evaluate(TURNS)
    with page.expect_request(gate.asks("PATCH")):
        to_list(run)
    names = page.locator(".sheets li strong")
    expect(names).to_have_text(["c", "b", "a"])
    with page.expect_response(f"{run.server}/api/sheets") as listed:
        answer(run, "a")
    listed.value.finished()
    expect(names.filter(has_text="Neu")).to_have_count(1)
    expect(names.filter(has_text=re.compile("^a$"))).to_have_count(0)


@pytest.mark.parametrize("reload", [False, True], ids=["at-once", "after-a-reload"])
def test_a_change_made_when_the_session_ran_out_is_kept_and_saved_after_the_login(run, reload):
    """I8: the save that finds the session gone brings the login, which says what waits; after
    the login the change is saved, with no reload, and after one too."""
    page, gate = start(run)
    gate.keep = False
    email = run.client.get("/api/me").json()["email"]
    page.context.clear_cookies()
    with page.expect_response(gate.answers("PATCH")) as turned_down:
        nudge(run)
        moved = at(page, "a").evaluate(LEFT)
        page.clock.run_for(2000)
    assert turned_down.value.status == 401
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    said = unsaved("a", "Melde dich neu an, dann wird sie gespeichert.")
    expect(page.locator(NOTICE)).to_have_text(said)
    # Nothing is tried while nobody is signed in.
    page.clock.run_for(60000)
    page.evaluate(TURNS)
    assert len(run.sent) == 1
    assert record(page, run.ids["a"])["doc"]["pages"][0]["blocks"][0]["x"] == 16
    page.clock.resume()
    if reload:
        page.reload()
        expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    # The session cookie is Secure and this server speaks http, so it goes by hand.
    cookie = {"name": "session", "value": run.client.cookies["session"], "url": run.server}
    page.context.add_cookies([cookie])
    page.get_by_label("E-Mail").fill(email)
    page.get_by_label("Passwort").fill(PASSWORD)
    page.get_by_role("button", name="Anmelden").click()
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    expect(page.locator(NOTICE)).to_have_count(0)
    assert x_of(run, "a") == 16
    assert record(page, run.ids["a"]) is None


def test_a_kept_change_is_saved_from_the_list_with_its_sheet_not_opened(run):
    """A7: the teacher who comes back to the list is not left with a change that sits."""
    page, _ = start(run)
    page.get_by_label("Titel", exact=True).fill("Neu")
    change(run)
    answer(run, "a", 500)
    # The failed save is over only once the page has read its answer: until then the save is under
    # way, and the tab that shuts sends nothing beside it (#933).
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    shut(page, 1)
    assert x_of(run, "a") == 15
    page, _, sent = again(run, None)
    names = page.locator(".sheets li strong")
    expect(names.filter(has_text="Neu")).to_have_count(1, timeout=5000)
    expect(page.locator(NOTICE)).to_have_count(0)
    assert len(sent) == 1
    assert sent[0].url.endswith(f"/api/sheets/{run.ids['a']}")
    assert x_of(run, "a") == 16
    assert run.held("a")["title"] == "Neu"
    assert record(page, run.ids["a"]) is None


def test_a_kept_change_of_a_sheet_changed_elsewhere_says_so_on_the_list(run):
    """I1: nothing is sent; the notice leads to the sheet, which asks which version stays."""
    page, _ = start(run)
    nudge(run)
    shut(page, 1)
    was = run.held("a")
    was["doc"]["pages"][0]["blocks"][0]["x"] = 40
    other = {"doc": was["doc"], "version": was["version"]}
    assert run.client.patch(f"/api/sheets/{run.ids['a']}", json=other).status_code == 200
    page, _, sent = again(run, None)
    said = page.locator(NOTICE)
    expect(said).to_have_text(
        "„a“ wurde auf einem anderen Gerät geändert. Öffne das Blatt, um zu wählen."
    )
    page.evaluate(TURNS)
    assert not sent
    assert x_of(run, "a") == 40
    said.get_by_role("link", name="Öffne das Blatt").click()
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    banner = page.locator(".clash")
    for name in ("Andere Version laden", "Mit dieser überschreiben"):
        expect(banner.get_by_role("button", name=name)).to_be_visible()
    expect(said).to_have_count(0)
    page.evaluate(TURNS)
    assert not sent
    assert x_of(run, "a") == 40
    assert record(page, run.ids["a"])["doc"]["pages"][0]["blocks"][0]["x"] == 16


def test_another_accounts_kept_change_is_neither_sent_nor_removed_at_the_start(run):
    """I2"""
    page, _ = start(run)
    nudge(run)
    shut(page, 1)
    page, _, sent = again(run, None, client=user())
    asked = []
    page.on("request", lambda r: asked.append(r.url))
    kept = record(page, run.ids["a"])
    assert kept["doc"]["pages"][0]["blocks"][0]["x"] == 16
    # Once more, with all that the tab asks for in view.
    reload(page, f"{run.server}/api/sheets")
    expect(page.get_by_role("heading", name="Meine Blätter")).to_be_visible()
    page.evaluate(TURNS)
    assert not sent
    assert not [url for url in asked if url.endswith(f"/api/sheets/{run.ids['a']}")]
    assert record(page, run.ids["a"]) == kept
    assert x_of(run, "a") == 15
