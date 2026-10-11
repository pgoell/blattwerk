"""What a teacher sees while a sheet loads (issue #313): the editor's frame with a white page where
the sheet comes to lie, at once, and the word `Lädt` on it when the load takes more than half a
second.

The tests hold back the account, the editor's script or the sheet, and let each go by hand. Where
time counts, Playwright's clock stands still and the test moves it: none waits on real time.
"""

import json
import re
from uuid import uuid4

import pytest
from conftest import IPAD, MEASURED, WEBKIT
from playwright.sync_api import expect
from ui import PASSWORD, TEXT, box, expect_picked, sheet, user

# What a sheet waits for: the account first, then the editor's script and the sheet side by side
# (#320).
ME = "**/api/me"
SCRIPT = "**/assets/Editor-*.js"
SHEET = "**/api/sheets/*"
BLANK = "main.editor:not([data-ready]) .desk > .sheet.blank"
READY = 'main.editor[data-ready="1"]'
# HELD: a test that moves a paused clock up to the word holds the script back, or lets React's
# own timer run out first (THROTTLE). With the sheet alone held, React draws the loading page anew
# when the script has come, at some real moment after its timer. Since #332 the app keeps the
# clock, so a page drawn anew sets no timer of its own and no longer waits on a clock that stands.
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

    def start(theme=None, touch=None, dark=False, signed=True):
        """`touch` is the window of a device with fingers, as IPAD."""
        look = {"viewport": touch or {"width": 1400, "height": 1000}, "has_touch": bool(touch)}
        if WEBKIT and touch:
            look = {**playwright.devices["iPad Pro 11"], "viewport": touch}
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


@pytest.mark.parametrize("first", [SCRIPT, SHEET], ids=["script-first", "sheet-first"])
def test_a_reload_shows_the_page_while_account_script_and_sheet_load(window, server, first):
    page, client = window()
    gates = {address: hold(page, address) for address in (ME, SCRIPT, SHEET)}
    page.goto(f"{server}/blatt/{sheet(client, [box('a', 'text', TEXT)])['id']}")
    expect_loading(page)
    # The script and the sheet are both asked for and held before the page is looked at again.
    with page.expect_request(SCRIPT), page.expect_request(SHEET):
        gates.pop(ME)()
    expect_loading(page)
    # Whichever of the two comes first, the page waits for the other.
    with page.expect_response(first):
        gates.pop(first)()
    expect_loading(page)
    gates.popitem()[1]()
    expect_ready(page, 1)


def test_the_sheet_is_asked_for_while_the_editors_script_is_on_its_way(window, server):
    """A17 (#320)"""
    page, client = window()
    go = hold(page, SCRIPT)
    with page.expect_request(SHEET):
        page.goto(f"{server}/blatt/{sheet(client, [box('a', 'text', TEXT)])['id']}")
    expect_loading(page)
    go()
    expect_ready(page, 1)
    # Away and back, the sheet is asked for anew.
    page.get_by_label("Meine Blätter").click()
    with page.expect_request(SHEET):
        page.locator(".sheets a").click()
    expect_ready(page, 1)


def test_a_sheet_that_is_not_there_says_so_though_the_script_comes_after(window, server):
    page, _ = window()
    errors = []
    page.on("pageerror", lambda error: errors.append(error))
    go = hold(page, SCRIPT)
    with page.expect_response(SHEET):
        page.goto(f"{server}/blatt/987654")
    expect_loading(page)
    go()
    expect(page.get_by_role("heading", name="Blatt nicht gefunden")).to_be_visible()
    assert not errors


def test_a_signed_out_reader_gets_the_login_after_the_loading_page(window, server):
    page, client = window(signed=False)
    go = hold(page, ME)
    page.goto(f"{server}/blatt/{sheet(client, [])['id']}")
    expect(page.locator(BLANK)).to_be_visible()
    go()
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    expect(page.locator("main.editor")).to_have_count(0)


def test_the_clock_starts_anew_when_a_reader_signs_in_on_a_sheets_address(window, server):
    page, _ = window(signed=False)
    email = f"{uuid4().hex}@example.com"
    client = user(email)
    # The script, not the sheet: see HELD.
    go = hold(page, SCRIPT)
    page.clock.install()
    page.clock.pause_at(page.evaluate("Date.now()") + 1000)
    page.goto(f"{server}/blatt/{sheet(client, [])['id']}")
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    # The reader takes more than half a second to sign in: that is no loading.
    page.clock.run_for(600)
    # The session cookie is Secure and this server speaks http, so it goes by hand.
    cookie = {"name": "session", "value": client.cookies["session"], "url": server}
    page.context.add_cookies([cookie])
    page.get_by_label("E-Mail").fill(email)
    page.get_by_label("Passwort").fill(PASSWORD)
    with page.expect_request(SCRIPT):
        page.get_by_role("button", name="Anmelden").click()
    said = page.locator(BLANK)
    expect(said).to_be_visible()
    expect(said).to_have_text("")
    page.clock.run_for(499)
    expect(said).to_have_text("")
    page.clock.run_for(1)
    expect(said).to_have_text("Lädt")
    go()
    page.clock.resume()
    expect(page.locator(READY)).to_be_visible(timeout=10000)


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
    # The account is there: the page is drawn anew, for the script and the sheet.
    with page.expect_request(SCRIPT), page.expect_request(SHEET):
        me()
    expect(said).to_have_text("")
    page.clock.run_for(99)
    expect(said).to_have_text("")
    page.clock.run_for(1)
    expect(said).to_have_text("Lädt")
    # Drawn anew once more, by the editor that waits for the sheet, it still says so. React shows
    # what has loaded only a while after the page that stood for it, by a timer of its own.
    with page.expect_response(SCRIPT):
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
    with page.expect_request(SCRIPT), page.expect_request(SHEET):
        me()
    with page.expect_response(SCRIPT):
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


# A phone's bar wraps to rows, and how many is up to the window's width alone: a long title adds
# none (#319).
PHONE = {"width": 390, "height": 844}
LONG = "Die Geschichte vom kleinen Igel, der nicht schlafen wollte."
CASES = {
    "blattform": (None, None, None),
    "plain": ("", None, None),
    "ipad": (None, IPAD, None),
    "phone": (None, PHONE, None),
    "phone-plain": ("", PHONE, None),
    "phone-long-title": (None, PHONE, LONG),
    **{f"phone-{wide}": (None, {**PHONE, "width": wide}, LONG) for wide in (320, 360, 414)},
}


@pytest.mark.parametrize(("theme", "touch", "title"), CASES.values(), ids=CASES)
def test_the_frame_and_the_page_lie_where_the_editor_puts_them(window, server, theme, touch, title):
    page, client = window(theme=theme, touch=touch)
    go = hold(page, SHEET)
    page.goto(f"{server}/blatt/{sheet(client, [], **({'title': title} if title else {}))['id']}")
    expect_loading(page)
    before = page.evaluate(PLACES)
    go()
    expect_ready(page)
    page.wait_for_function(MEASURED, timeout=10000)
    after = page.evaluate(PLACES)
    assert before.keys() == after.keys()
    exact = {part for part, was in before.items() if not isinstance(was, list)}
    moved = {
        part: (was, after[part])
        for part, was in before.items()
        if after[part] != (was if part in exact else pytest.approx(was, abs=1))
    }
    assert not moved
    # Nor did the page lie elsewhere for a frame between the two, as when the editor drew it
    # small before it had measured the desk.
    assert page.evaluate(SHIFTS) == 0
    # An upright A4 page, and the layout the case is about.
    assert before[".sheet"][3] / before[".sheet"][2] == pytest.approx(297 / 210, abs=0.01)
    assert before["leaf"] == (theme is None and not touch)
    assert (before[".panel"] is None) == (touch is IPAD)
    # A phone's bar has more rows than one, or the case shows nothing.
    assert (before["header"][3] > 100) == (touch is not None and touch["width"] <= 700)


def test_a_screen_reader_hears_that_it_loads(window, server):
    page, client = window()
    # The script, not the sheet: see HELD.
    go = hold(page, SCRIPT)
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


def light(colour):
    """How light a colour of the screen is, from 0 to 1, as the rule for contrast counts it."""
    parts = [int(n) / 255 for n in re.findall(r"\d+", colour)[:3]]
    red, green, blue = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in parts)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


@pytest.mark.parametrize("theme", ["", None], ids=["plain", "blattform"])
def test_the_loading_page_is_white_on_a_dark_desk_and_its_word_reads(window, server, theme):
    page, client = window(theme=theme, dark=True)
    # The script, not the sheet: see HELD.
    go = hold(page, SCRIPT)
    page.clock.install()
    page.clock.pause_at(page.evaluate("Date.now()") + 1000)
    page.goto(f"{server}/blatt/{sheet(client, [])['id']}")
    expect_loading(page)
    colour = "el => getComputedStyle(el).backgroundColor"
    white = page.locator(".sheet.blank").evaluate(colour)
    assert white == "rgb(255, 255, 255)"
    # Blattform keeps its pale desk on a dark device.
    assert (light(page.locator(".desk").evaluate(colour)) < 0.05) == (theme == "")
    # The word is dark enough on the white page, whatever the theme makes of its other greys.
    page.clock.run_for(500)
    expect(page.locator(BLANK)).to_have_text("Lädt")
    word = page.locator(".sheet.blank").evaluate("el => getComputedStyle(el).color")
    assert (light(white) + 0.05) / (light(word) + 0.05) >= 4.5
    go()
    page.clock.resume()
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
