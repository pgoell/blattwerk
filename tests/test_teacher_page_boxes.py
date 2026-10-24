"""The teacher-page tool answers the page's boxes, including one left open by a dead verb."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

from uuid import uuid4

import pytest
from playwright.sync_api import expect
from test_teacher_page import (
    ONE,
    folder,  # noqa: F401
    pytestmark,  # noqa: F401
    run,
    tool,
)
from ui import (
    PASSWORD,
    box,
    sheet,
    user,
)


def test_a_box_is_answered_no_and_named_and_box_yes_answers_yes(browser):
    page = browser.new_page()
    asked = tool.answered(page, yes=False)
    assert page.evaluate("confirm('Weg?')") is False
    assert asked == [("confirm", "Weg?")]
    page.close()
    page = browser.new_page()
    asked = tool.answered(page, yes=True)
    assert page.evaluate("confirm('Ja?')") is True
    assert asked == [("confirm", "Ja?")]
    page.close()


def test_a_box_nobody_answered_in_time_is_answered_no(browser):
    # The holder's way: it remembers each box with its time, and `overdue` says no to the old ones.
    page = browser.new_page()
    waiting: list = []
    page.on("dialog", tool.remember(waiting))
    with page.expect_event("dialog"):
        page.evaluate("setTimeout(() => (window.said = confirm('Weg?')), 0)")
    assert len(waiting) == 1
    # A young box stays open: it is still on the list, and no answer has gone out.
    tool.overdue(waiting, now=waiting[0][1] + 1)
    assert len(waiting) == 1
    tool.overdue(waiting, now=waiting[0][1] + tool.PATIENCE + 1)
    assert waiting == []
    page.wait_for_function("window.said === false")
    assert page.evaluate("1 + 1") == 2
    page.close()


def test_a_box_a_verb_answered_first_is_no_error_for_the_holder(browser):
    page = browser.new_page()
    waiting: list = []
    page.on("dialog", tool.remember(waiting))
    asked = tool.answered(page, yes=True)
    with page.expect_event("dialog"):
        page.evaluate("setTimeout(() => (window.said = confirm('Ja?')), 0)")
    page.wait_for_function("window.said === true")
    # The second answer raises inside `overdue`, and the holder shrugs it off.
    tool.overdue(waiting, now=waiting[0][1] + tool.PATIENCE + 1)
    assert waiting == []
    assert asked == [("confirm", "Ja?")]
    page.close()


@pytest.mark.parametrize("words", [["box"], ["box", "yes"], ["box", "maybe", "click", "PDF"]])
def test_box_refuses_what_is_no_answer_in_plain_words(folder, server, words):
    done = run(folder, server, *words)
    assert done.returncode == 1 and done.stdout == ""
    assert done.stderr.startswith('box takes yes or no, then a verb: box yes click "Löschen"')
    assert "Traceback" not in done.stderr


@pytest.mark.native
def test_a_click_on_a_box_names_it_and_box_yes_takes_the_yes_answer(folder, server):
    # The app's delete asks `Blatt „Probe“ löschen?`: the plain click says no, `box yes` says yes.
    email = f"{uuid4().hex}@example.com"
    client = user(email)
    made = sheet(client, [box("a", "text", ONE)], title="Probe")

    def ok(*words):
        done = run(folder, server, *words)
        assert done.returncode == 0, (words, done.stdout, done.stderr)
        return done.stdout

    try:
        ok("start")
        ok("click", "E-Mail")
        ok("type", email)
        ok("click", "Passwort")
        ok("type", PASSWORD)
        ok("key", "Enter")
        ok("where", "Neues Blatt")
        said = ok("click", "Probe löschen")
        assert 'A box asked: "Blatt „Probe“ löschen?" (confirm). Answered no.' in said
        assert client.get(f"/api/sheets/{made['id']}").status_code == 200
        said = ok("box", "yes", "click", "Probe löschen")
        assert "Answered yes." in said
        assert client.get(f"/api/sheets/{made['id']}").status_code == 404
    finally:
        run(folder, server, "stop")


@pytest.mark.native
def test_open_meets_the_leave_question_stays_on_no_and_goes_on_box_yes(folder, server, monkeypatch):
    # A typed text is unsaved until the save goes out. Two verbs stand between the typing and
    # `open`. On a loaded runner they take longer than the teacher's 2 s, and the page then leaves
    # with no question. The page waits 20 s, so `open` still meets the change.
    monkeypatch.setenv("TEACHER_SAVE_AFTER", "20000")
    email = f"{uuid4().hex}@example.com"
    client = user(email)
    made = sheet(client, [box("a", "text", ONE)], title="Probe")

    def ok(*words):
        done = run(folder, server, *words)
        assert done.returncode == 0, (words, done.stdout, done.stderr)
        return done.stdout

    try:
        ok("start")
        ok("click", "E-Mail")
        ok("type", email)
        ok("click", "Passwort")
        ok("type", PASSWORD)
        ok("key", "Enter")
        ok("click", "Probe")
        ok("where", "Gespeichert")
        ok("click", "Eins")
        ok("key", "Enter")
        ok("type", " Neu")
        ok("key", "Escape")
        said = ok("open", "/")
        assert 'A box asked: "" (beforeunload). Answered no.' in said
        assert "To say yes: box yes open /" in said
        assert ok("where", "Neu").startswith("Neu at ")
        ok("box", "yes", "open", "/")
        assert ok("where", "Neues Blatt").startswith("Neues Blatt at ")
    finally:
        run(folder, server, "stop")
    assert client.get(f"/api/sheets/{made['id']}").status_code == 200


@pytest.mark.native
def test_the_answer_key_shows_by_mehr_and_its_item_in_two_calls(folder, server, playwright):
    """#773: in the window of 1280 px "Lösungen zeigen" lies under "Mehr", and one call opens the
    menu while the next, a client of its own, clicks the item."""
    email = f"{uuid4().hex}@example.com"
    client = user(email)
    sheet(client, [box("a", "text", ONE)], title="Probe")

    def ok(*words):
        done = run(folder, server, *words)
        assert done.returncode == 0, (words, done.stdout, done.stderr)
        return done.stdout

    try:
        ok("start")
        ok("click", "E-Mail")
        ok("type", email)
        ok("click", "Passwort")
        ok("type", PASSWORD)
        ok("key", "Enter")
        ok("click", "Probe")
        ok("click", "Beenden")
        ok("where", "Gespeichert")
        assert run(folder, server, "where", "Lösungen zeigen").returncode == 1
        ok("click", "Mehr")
        ok("click", "Lösungen zeigen")
        ok("click", "Mehr")
        joined = playwright.chromium.connect_over_cdp(tool.running()["endpoint"])
        item = joined.contexts[0].pages[0].get_by_role("menuitemcheckbox", name="Lösungen zeigen")
        expect(item).to_have_attribute("aria-checked", "true")
        joined.close()
    finally:
        run(folder, server, "stop")


@pytest.mark.native
def test_a_box_left_open_by_a_dead_verb_is_answered_no_and_the_next_verb_acts(
    folder, server, playwright
):
    # The verb's client is gone with its box open: only the holder can answer that box now.
    limit = tool.PATIENCE + 10

    def join():
        """A client of the holder's window, as a verb is one, on the suite's own Playwright."""
        client = playwright.chromium.connect_over_cdp(tool.running()["endpoint"])
        page = client.contexts[0].pages[0]
        # A client that answers nothing: Playwright would otherwise dismiss the box by itself.
        page.on("dialog", lambda dialog: None)
        return client, page

    try:
        started = run(folder, server, "start")
        assert started.returncode == 0, (started.stdout, started.stderr)
        client, page = join()
        with page.expect_event("dialog"):
            page.evaluate("setTimeout(() => (window.said = confirm('Weg?')), 0)")
        client.close()
        # The page waits on the open box; the holder's no is what frees it for the next verb.
        done = run(folder, server, "where", "Anmelden", limit=limit)
        assert done.returncode == 0, (done.stdout, done.stderr)
        assert done.stdout.startswith("Anmelden at ") and "A box asked" not in done.stdout
        client, page = join()
        assert page.evaluate("window.said") is False
        client.close()
    finally:
        run(folder, server, "stop")
