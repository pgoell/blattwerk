"""Meine Blätter says `Lädt` once its list has taken half a second (issue #365), as a sheet does
(test_loading.py): not before, not when the list stands, and not when the load failed.

The tests hold the list back and let it go by hand. The page's clock stands still and the test
moves it: none waits on real time.
"""

# The fixtures `window` and `run` are imported, and each test names one as its argument.
# ruff: noqa: F811

from playwright.sync_api import expect
from test_load_fails import expect_list_failed, fail
from test_loading import hold, window  # noqa: F401
from test_saves import answer, leave, run  # noqa: F401
from test_stale import TURNS
from ui import TEXT, box, sheet

SAID = "main [role=status]"
# Notes, before the browser paints, whether the list ever said that it loads.
HEARD = """
new MutationObserver(() => {
    if (document.querySelector('main [role=status]')?.textContent) window.loading = true;
}).observe(document, { subtree: true, childList: true, characterData: true });
"""


def asked(page, server, client):
    """Goes to the list of one sheet with the clock held and the list held back. Gives what lets
    the list go."""
    sheet(client, [box("a", "text", TEXT)])
    page.add_init_script(HEARD)
    go = hold(page, f"{server}/api/sheets")
    page.clock.install()
    page.clock.pause_at(page.evaluate("Date.now()") + 1000)
    with page.expect_request(f"{server}/api/sheets"):
        page.goto(server)
    expect(page.get_by_role("button", name="Neues Blatt")).to_be_visible()
    return go


def test_the_list_says_that_it_loads_after_half_a_second(window, server):
    """A27"""
    page, client = window()
    go = asked(page, server, client)
    said = page.locator(SAID)
    expect(said).to_have_text("")
    page.clock.run_for(400)
    page.evaluate(TURNS)
    expect(said).to_have_text("")
    page.clock.run_for(99)
    page.evaluate(TURNS)
    expect(said).to_have_text("")
    page.clock.run_for(1)
    expect(said).to_have_text("Lädt")
    go()
    expect(page.locator(".sheets li")).to_have_count(1)
    expect(said).to_have_count(0)
    expect(page.locator("main")).not_to_contain_text("Lädt")


def test_a_list_that_comes_soon_never_says_that_it_loads(window, server):
    """A27"""
    page, client = window()
    go = asked(page, server, client)
    page.clock.run_for(400)
    go()
    expect(page.locator(".sheets li")).to_have_count(1)
    page.clock.run_for(1000)
    page.evaluate(TURNS)
    expect(page.locator(SAID)).to_have_count(0)
    assert not page.evaluate("window.loading")


def test_a_list_that_stands_says_no_word_while_it_is_asked_for_anew(run):
    """A27: the list asks anew when a save lands, and stands as it is until the answer comes."""
    page, _ = leave(run, "held", "list")
    address = f"{run.server}/api/sheets"
    go = hold(page, address)
    with page.expect_request(address):
        answer(run, "a")
    page.clock.run_for(1000)
    page.evaluate(TURNS)
    expect(page.locator(".sheets li")).to_have_count(3)
    expect(page.locator(SAID)).to_have_count(0)
    with page.expect_response(address):
        go()
    expect(page.locator(".sheets li")).to_have_count(3)
    expect(page.locator(SAID)).to_have_count(0)


def test_a_list_whose_load_failed_does_not_say_that_it_loads(window, server):
    """A27: the failure stands in its place, and a new try starts the half second anew."""
    page, client = window()
    sheet(client, [box("a", "text", TEXT)])
    address = f"{server}/api/sheets"
    fail(page, address)
    page.clock.install()
    page.clock.pause_at(page.evaluate("Date.now()") + 1000)
    page.goto(server)
    press = expect_list_failed(page)
    said = page.locator(SAID)
    page.clock.run_for(1000)
    page.evaluate(TURNS)
    expect(said).to_have_count(0)
    page.unroute(address)
    go = hold(page, address)
    with page.expect_request(address):
        press.click()
    expect(said).to_have_text("")
    page.clock.run_for(499)
    page.evaluate(TURNS)
    expect(said).to_have_text("")
    page.clock.run_for(1)
    expect(said).to_have_text("Lädt")
    go()
    expect(page.locator(".sheets li")).to_have_count(1)
    expect(said).to_have_count(0)
