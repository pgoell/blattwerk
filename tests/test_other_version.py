"""A clash's choice that the server does not answer says so and stands again (issue #338): after
a failure, and after 20 s with no answer. While it is under way the banner says that it loads and
takes no second press. The kept change is safe until the other version has truly come.

Built on test_saves.py: the sheet A in a clash, and its gate, which holds the load a choice asks
for. The page's clock stands and the test moves it.

The docstrings name the lines of the checklist.
"""

# The fixtures `window` and `run` are imported, and each test names one as its argument.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_load_fails import loads
from test_loading import expect_ready, window  # noqa: F401
from test_saves import CHOICES, LEFT, clash, kept_x, record, run, start, x_of  # noqa: F401
from test_stale import STATUS, TURNS
from ui import at

LOAD, OVER = CHOICES
BUSY = "Lädt …"
WORD = "Das hat nicht geklappt. Prüfe deine Verbindung und versuche es noch einmal."
HOW = [500, "cut", "never"]


def press(run, choice):
    """Presses the choice with its load held. Gives that load."""
    page, gate = run.page, run.gates["a"]
    gate.free = False
    with page.expect_request(gate.asks("GET")):
        page.locator(".clash").get_by_role("button", name=choice).click()
    page.evaluate(TURNS)
    return gate.loads.pop()


def fail(run, choice, how):
    """Presses the choice, and its load fails: with a status, with the line "cut", or with no
    answer for 20 s, "never". From then on the server answers."""
    page, gate = run.page, run.gates["a"]
    route = press(run, choice)
    if how == "never":
        page.clock.run_for(19999)
        page.evaluate(TURNS)
        expect_busy(page)
        assert not route.request.failure
        with page.expect_event("requestfailed", gate.asks("GET")):
            page.clock.run_for(1)
    elif how == "cut":
        with page.expect_event("requestfailed", gate.asks("GET")):
            route.abort()
    else:
        with page.expect_response(gate.answers("GET")):
            route.fulfill(status=how)
    page.evaluate(TURNS)
    gate.free = True


def expect_busy(page):
    banner = page.locator(".clash")
    expect(banner).to_contain_text(BUSY)
    expect(banner).not_to_contain_text(WORD)
    for name in CHOICES:
        expect(banner.get_by_role("button", name=name)).to_be_disabled()


def expect_word(page):
    """The banner says that it did not work, and both choices stand again."""
    banner = page.locator(".clash")
    expect(banner).to_contain_text(WORD)
    expect(banner).not_to_contain_text(BUSY)
    for name in CHOICES:
        expect(banner.get_by_role("button", name=name)).to_be_enabled()
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")


def test_the_other_version_with_no_answer_ends_after_20_s_and_says_so(run):
    """A1"""
    page, _ = start(run)
    clash(run)
    fail(run, LOAD, "never")
    expect_word(page)


@pytest.mark.parametrize("how", [500, "cut"])
def test_the_other_version_whose_load_fails_says_so(run, how):
    """A2"""
    page, _ = start(run)
    clash(run)
    errors = []
    page.on("pageerror", lambda error: errors.append(error))
    fail(run, LOAD, how)
    expect_word(page)
    assert not errors


@pytest.mark.parametrize("how", HOW)
def test_the_other_version_loads_at_the_next_press_once_the_server_answers(run, how):
    """A3: the editor shows it, and the kept change is dropped."""
    page, _ = start(run)
    clash(run)
    moved = at(page, "a").evaluate(LEFT)
    fail(run, LOAD, how)
    banner = page.locator(".clash")
    banner.get_by_role("button", name=LOAD).click()
    expect(banner).to_have_count(0)
    expect(at(page, "a")).not_to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    assert record(page, run.ids["a"]) is None
    assert x_of(run, "a") == 99
    assert len(run.sent) == 1


def test_the_kept_change_is_safe_until_the_other_version_has_loaded(run):
    """A4: through a held and a failed load the editor shows the change, the browser's store
    holds it and nothing is sent; a reload brings the change and the banner back."""
    page, gate = start(run)
    clash(run)
    moved = at(page, "a").evaluate(LEFT)
    kept = record(page, run.ids["a"])
    assert kept_x(page, run) == 16

    def safe():
        expect(at(page, "a")).to_have_css("left", moved)
        assert record(page, run.ids["a"]) == kept
        assert len(run.sent) == 1
        assert x_of(run, "a") == 99

    route = press(run, LOAD)
    page.clock.run_for(10000)
    page.evaluate(TURNS)
    expect_busy(page)
    safe()
    with page.expect_response(gate.answers("GET")):
        route.fulfill(status=500)
    page.evaluate(TURNS)
    expect_word(page)
    safe()
    gate.free = True
    page.clock.resume()
    page.reload()
    expect_ready(page, 1)
    banner = page.locator(".clash")
    for name in CHOICES:
        expect(banner.get_by_role("button", name=name)).to_be_enabled()
    expect(banner).not_to_contain_text(WORD)
    page.evaluate(TURNS)
    expect(at(page, "a")).to_have_css("left", moved)
    assert record(page, run.ids["a"])["doc"] == kept["doc"]
    assert len(run.sent) == 1
    assert x_of(run, "a") == 99


@pytest.mark.parametrize("choice", CHOICES)
def test_a_choice_under_way_says_so_and_takes_no_second_press(run, choice):
    """I1: one load goes."""
    page, gate = start(run)
    clash(run)
    asked = loads(page, f"{run.server}/api/sheets/{run.ids['a']}")
    route = press(run, choice)
    expect_busy(page)
    # A press on a button that is off does nothing.
    for name in CHOICES:
        page.locator(".clash").get_by_role("button", name=name).click(force=True)
    page.evaluate(TURNS)
    assert len(asked) == 1
    assert not gate.loads
    gate.free, gate.keep = True, False
    route.continue_()
    expect(page.locator(".clash")).to_have_count(0)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    assert len(asked) == 1
    assert x_of(run, "a") == (99 if choice == LOAD else 16)


@pytest.mark.parametrize("how", HOW)
def test_overwriting_that_fails_says_so_and_saves_at_the_next_press(run, how):
    """I2"""
    page, gate = start(run)
    clash(run)
    moved = at(page, "a").evaluate(LEFT)
    fail(run, OVER, how)
    expect_word(page)
    assert len(run.sent) == 1
    assert x_of(run, "a") == 99
    gate.keep = False
    banner = page.locator(".clash")
    with page.expect_response(lambda r: gate.answers("PATCH")(r) and r.ok) as saved:
        banner.get_by_role("button", name=OVER).click()
    saved.value.finished()
    expect(banner).to_have_count(0)
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(at(page, "a")).to_have_css("left", moved)
    assert x_of(run, "a") == 16
    assert record(page, run.ids["a"]) is None


@pytest.mark.parametrize("choice", CHOICES)
def test_the_word_is_told_as_an_alert_and_goes_with_the_next_press(run, choice):
    """I3"""
    page, _ = start(run)
    clash(run)
    fail(run, choice, 500)
    told = page.get_by_role("alert")
    expect(told).to_have_count(1)
    expect(told).to_contain_text(WORD)
    press(run, choice)
    expect(told).not_to_contain_text(WORD)
    expect_busy(page)
