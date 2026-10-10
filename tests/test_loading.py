"""What a teacher sees while a sheet loads (issue #313): the editor's frame with a white page where
the sheet comes to lie, at once, and the word `Lädt` on it when the load takes more than half a
second.

The tests hold back the account, the editor's script or the sheet, and let each go by hand. Where
time counts, Playwright's clock stands still and the test moves it: none waits on real time.
"""

import json
import re

import pytest
from conftest import IPAD, MEASURED, WEBKIT
from playwright.sync_api import expect
from ui import TEXT, box, expect_picked, sheet, user

# What a sheet waits for, in the order it asks for them.
ME = "**/api/me"
SCRIPT = "**/assets/Editor-*.js"
SHEET = "**/api/sheets/*"
BLANK = "main.editor:not([data-ready]) .desk > .sheet.blank"
READY = 'main.editor[data-ready="1"]'
# React shows what a held script brought no sooner than this many ms after the page that stood
# for it.
THROTTLE = 300
# Notes, before the browser paints, what must never be seen: `bare`, an editor with no page on its
# desk; `flash`, the app's bar or footer on a sheet's address; `said`, the word that it loads.
WATCH = """
new MutationObserver(() => {
    const one = (css) => document.querySelector(css);
    const drawn = (el) => el.getClientRects().length;
    const seen = (css) => [...document.querySelectorAll(css)].some(drawn);
    const sheet = location.pathname.startsWith('/blatt/');
    if (one('main.editor') && !one('.desk > .sheet')) window.bare = true;
    if (sheet && seen('#root > nav, #root > footer')) window.flash = true;
    if (one('.sheet.blank')?.textContent) window.said = true;
}).observe(document, { subtree: true, childList: true, attributes: true, characterData: true });
// Chromium tells when a page moved or changed its size from one frame to the next.
window.shifts = 0;
if (PerformanceObserver.supportedEntryTypes.includes('layout-shift'))
    new PerformanceObserver((list) => {
        for (const entry of list.getEntries())
            if (entry.sources.some((from) => from.node?.matches?.('.sheet'))) window.shifts += 1;
    }).observe({ type: 'layout-shift', buffered: true });
"""
# The shifts so far, read two frames on: the browser tells of one only after it has painted it.
SHIFTS = """() => new Promise((done) =>
    requestAnimationFrame(() => requestAnimationFrame(() => done(window.shifts))))"""
# Where the frame's parts and the first page lie, whether the desk has a scrollbar, and how wide.
PLACES = """() => {
    const box = (el) => ['x', 'y', 'width', 'height'].map((n) => el.getBoundingClientRect()[n]);
    const main = document.querySelector('main.editor'), desk = main.querySelector('.desk');
    const parts = ['header', '.left', '.stage', '.desk', '.panel', '.sheet'].map((css) => {
        const all = [...main.querySelectorAll(css)];
        return [css, all.length > 1 ? 'two' : all.length ? box(all[0]) : null];
    });
    return {
        ...Object.fromEntries(parts),
        scrolls: desk.scrollHeight > desk.clientHeight,
        bar: desk.offsetWidth - desk.clientWidth,
        leaf: main.classList.contains('leaf'),
    };
}"""


@pytest.fixture
def window(browser, server, playwright):
    """Gives a page of a new user that is on no address yet, and the user's client.

    As the fixture `editor` opens it, but the test goes to the address itself, after it has said
    what to hold back.
    """
    contexts = []

    def start(theme=None, touch=False, dark=False, signed=True):
        look = {"viewport": IPAD if touch else {"width": 1400, "height": 1000}, "has_touch": touch}
        if WEBKIT and touch:
            look = {**playwright.devices["iPad Pro 11"], "viewport": IPAD}
        context = browser.new_context(**look, color_scheme="dark" if dark else "light")
        contexts.append(context)
        # The tour would open on the first visit and lie over the sheet.
        context.add_init_script("localStorage.setItem('tour', '1')")
        if theme is not None:
            context.add_init_script(f"localStorage.setItem('theme', {json.dumps(theme)})")
        context.add_init_script(WATCH)
        client = user()
        if signed:
            # The session cookie is Secure and this server speaks http, so it goes by hand.
            context.add_cookies(
                [{"name": "session", "value": client.cookies["session"], "url": server}]
            )
        return context.new_page(), client

    yield start
    for context in contexts:
        context.close()


def hold(page, address):
    """Holds back what the page reads from the address. Gives what lets it go, from then on."""
    kept, free = [], []

    def came(route):
        # A save is not a load.
        if free or route.request.method != "GET":
            route.continue_()
        else:
            kept.append(route)

    page.route(address, came)

    def go():
        free.append(True)
        for route in kept:
            route.continue_()

    return go


def expect_loading(page):
    """The loading page stands as the brief's and the fixture's waits need it: not ready, with no
    block, and with neither of the words they wait for."""
    expect(page.locator(BLANK)).to_be_visible()
    expect(page.locator(".sheet")).to_have_count(1)
    expect(page.locator(".block[data-id]")).to_have_count(0)
    expect(page.locator("#root > nav, #root > footer").locator("visible=true")).to_have_count(0)
    for word in ("Gespeichert", "Neues Blatt"):
        expect(page.locator("body")).not_to_contain_text(word)


def expect_ready(page, blocks=0):
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    expect(page.locator(".sheet.blank")).to_have_count(0)
    expect(page.locator(".block[data-id]")).to_have_count(blocks)
    # From the click or the address to the editor, the desk was never empty and the app's bar
    # never showed.
    assert not page.evaluate("window.bare || window.flash")


def test_a_new_sheet_shows_its_page_while_it_loads(window, server):
    page, _ = window()
    page.goto(server)
    go = hold(page, SHEET)
    page.get_by_role("button", name="Neues Blatt").click()
    expect_loading(page)
    go()
    expect_ready(page)
    expect(page.locator(".top")).to_contain_text("Gespeichert")


def test_a_sheet_picked_from_the_list_shows_its_page_while_it_loads(window, server):
    page, client = window()
    sheet(client, [box("a", "text", TEXT)])
    page.goto(server)
    go = hold(page, SHEET)
    page.locator(".sheets a").click()
    expect_loading(page)
    go()
    expect_ready(page, 1)


def test_a_reload_shows_the_page_while_account_script_and_sheet_load(window, server):
    page, client = window()
    gates = [hold(page, address) for address in (ME, SCRIPT, SHEET)]
    page.goto(f"{server}/blatt/{sheet(client, [box('a', 'text', TEXT)])['id']}")
    for go, then in zip(gates, (SCRIPT, SHEET, None), strict=True):
        expect_loading(page)
        if then:
            # The next of the three is asked for and held before this one is looked at again.
            with page.expect_request(then):
                go()
        else:
            go()
    expect_ready(page, 1)


def test_a_signed_out_reader_gets_the_login_after_the_loading_page(window, server):
    page, client = window(signed=False)
    go = hold(page, ME)
    page.goto(f"{server}/blatt/{sheet(client, [])['id']}")
    expect(page.locator(BLANK)).to_be_visible()
    go()
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    expect(page.locator("main.editor")).to_have_count(0)


def test_the_word_comes_half_a_second_after_the_page_with_the_script_held(window, server):
    page, client = window()
    go = hold(page, SCRIPT)
    page.clock.install()
    page.clock.pause_at(page.evaluate("Date.now()") + 1000)
    with page.expect_request(SCRIPT):
        page.goto(f"{server}/blatt/{sheet(client, [])['id']}")
    said = page.get_by_role("status")
    expect_loading(page)
    expect(said).to_have_text("")
    page.clock.run_for(499)
    expect(said).to_have_text("")
    page.clock.run_for(1)
    expect(said).to_have_text("Lädt")
    expect(page.locator(BLANK)).to_have_text("Lädt")
    assert page.evaluate("window.said")
    go()
    page.clock.resume()
    expect_ready(page)


def test_one_clock_runs_over_account_script_and_sheet(window, server):
    page, client = window()
    me, script, held = (hold(page, address) for address in (ME, SCRIPT, SHEET))
    page.clock.install()
    page.clock.pause_at(page.evaluate("Date.now()") + 1000)
    page.goto(f"{server}/blatt/{sheet(client, [])['id']}")
    said = page.get_by_role("status")
    expect(said).to_have_text("")
    page.clock.run_for(400)
    # The account is there: the page is drawn anew, for the script.
    with page.expect_request(SCRIPT):
        me()
    expect(said).to_have_text("")
    page.clock.run_for(99)
    expect(said).to_have_text("")
    page.clock.run_for(1)
    expect(said).to_have_text("Lädt")
    # Drawn anew once more, for the sheet, it still says so. React shows what has loaded only a
    # while after the page that stood for it, by a timer of its own.
    with page.expect_request(SHEET):
        script()
        page.clock.run_for(THROTTLE)
    expect(said).to_have_text("Lädt")
    assert not page.evaluate("window.bare")
    held()
    page.clock.resume()
    expect_ready(page)


def test_a_load_within_half_a_second_never_says_that_it_loads(window, server):
    page, client = window()
    me, script, held = (hold(page, address) for address in (ME, SCRIPT, SHEET))
    page.clock.install()
    page.clock.pause_at(page.evaluate("Date.now()") + 1000)
    page.goto(f"{server}/blatt/{sheet(client, [])['id']}")
    expect(page.locator(BLANK)).to_be_visible()
    page.clock.run_for(100)
    with page.expect_request(SCRIPT):
        me()
    with page.expect_request(SHEET):
        script()
        page.clock.run_for(THROTTLE)
    page.clock.run_for(499 - 100 - THROTTLE)
    held()
    # The editor stands while the clock does, a thousandth of a second before the word was due.
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    page.clock.run_for(1000)
    page.clock.resume()
    expect_ready(page)
    assert not page.evaluate("window.said")


CASES = {"blattform": (None, False), "plain": ("", False), "ipad": (None, True)}


@pytest.mark.parametrize(("theme", "touch"), CASES.values(), ids=CASES)
def test_the_frame_and_the_page_lie_where_the_editor_puts_them(window, server, theme, touch):
    page, client = window(theme=theme, touch=touch)
    go = hold(page, SHEET)
    page.goto(f"{server}/blatt/{sheet(client, [])['id']}")
    expect_loading(page)
    before = page.evaluate(PLACES)
    go()
    expect_ready(page)
    page.wait_for_function(MEASURED, timeout=10000)
    after = page.evaluate(PLACES)
    assert before.keys() == after.keys()
    for part, was in before.items():
        now = after[part]
        if isinstance(was, list):
            assert now == pytest.approx(was, abs=1), part
        else:
            assert now == was, part
    # Nor did the page lie elsewhere for a frame between the two, as when the editor drew it
    # small before it had measured the desk.
    assert page.evaluate(SHIFTS) == 0
    # An upright A4 page, and the layout the case is about.
    assert before[".sheet"][3] / before[".sheet"][2] == pytest.approx(297 / 210, abs=0.01)
    assert before["leaf"] == (theme is None and not touch)
    assert (before[".panel"] is None) == touch


def test_a_screen_reader_hears_that_it_loads(window, server):
    page, client = window()
    go = hold(page, SHEET)
    page.clock.install()
    page.clock.pause_at(page.evaluate("Date.now()") + 1000)
    page.goto(f"{server}/blatt/{sheet(client, [])['id']}")
    said = page.locator(".sheet.blank[role=status]")
    # Empty at first, so that the word is a change, which is what a screen reader reads out.
    expect(said).to_have_text("")
    page.clock.run_for(500)
    expect(said).to_have_text("Lädt")
    expect(page.get_by_role("status")).to_have_count(1)
    go()
    page.clock.resume()
    expect_ready(page)


def test_a_sheet_that_is_not_there_says_so_after_the_loading_page(window, server):
    page, _ = window()
    go = hold(page, SHEET)
    page.goto(f"{server}/blatt/987654")
    expect_loading(page)
    go()
    expect(page.get_by_role("heading", name="Blatt nicht gefunden")).to_be_visible()
    expect(page.locator("main.editor")).to_have_count(0)
    expect(page.locator("#root > nav")).to_be_visible()


def test_the_loading_page_is_white_on_a_dark_desk(window, server):
    page, client = window(theme="", dark=True)
    go = hold(page, SHEET)
    page.goto(f"{server}/blatt/{sheet(client, [])['id']}")
    expect_loading(page)
    colour = "el => getComputedStyle(el).backgroundColor"
    white = page.locator(".sheet.blank").evaluate(colour)
    assert white == "rgb(255, 255, 255)"
    red, green, blue = map(int, re.findall(r"\d+", page.locator(".desk").evaluate(colour))[:3])
    assert max(red, green, blue) < 64
    go()
    expect_ready(page)
    assert page.locator(".sheet").evaluate(colour) == white


def test_keys_pressed_while_it_loads_do_no_harm_and_the_editor_takes_them_after(window, server):
    page, client = window()
    errors = []
    page.on("pageerror", lambda error: errors.append(error))
    go = hold(page, SHEET)
    page.goto(f"{server}/blatt/{sheet(client, [box('a', 'text', TEXT)])['id']}")
    expect_loading(page)
    for key in ("Control+a", "Delete", "ArrowDown", "Enter", "x", "Escape", "Control+z", "Tab"):
        page.keyboard.press(key)
    go()
    expect_ready(page, 1)
    page.keyboard.press("Control+a")
    expect_picked(page, "a")
    top = page.locator(".block.sel").evaluate("el => getComputedStyle(el).top")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).not_to_have_css("top", top)
    assert not errors
