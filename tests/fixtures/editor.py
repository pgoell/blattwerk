"""The browser, and an editor page on a sheet of the given blocks."""

import json
import os

import pytest
from playwright.sync_api import expect, sync_playwright
from ui import BROWSER, SETTLED, sheet, user

WEBKIT = BROWSER == "webkit"
# The headed lane, `mise run test:native`: a real window, where a list and a colour picker open.
NATIVE = os.environ.get("BLATTWERK_NATIVE") == "1"
IPAD = {"width": 834, "height": 1194}
TURNED = {"width": 1194, "height": 834}
# Whether the widest page fills the desk's width, as it does at a zoom of 100 % once the editor
# has measured the desk.
MEASURED = """() => {
    const desk = document.querySelector('.desk'), look = getComputedStyle(desk);
    const room = desk.clientWidth - parseFloat(look.paddingLeft) - parseFloat(look.paddingRight);
    const sheets = [...desk.querySelectorAll('.sheet')];
    const widest = Math.max(...sheets.map((el) => el.getBoundingClientRect().width));
    return Math.abs(widest - room) < 1;
}"""
# WebKit on Linux gives Control+V the picture, then clipboard.read() returns that item with no
# type. Einfügen reads, so the picture is missing (#204). The bytes stay in the item the page
# wrote: keep them, and put the type back when a read finds none.
READ_PICTURE = """(() => {
    const clip = navigator.clipboard;
    if (!clip || !clip.write || clip.write.kept) return;
    const write = clip.write.bind(clip);
    const writeText = clip.writeText.bind(clip);
    const read = clip.read.bind(clip);
    let kept = null;
    const remember = async (items) => {
        const parts = {};
        for (const item of items) {
            for (const type of item.types) {
                const blob = await item.getType(type);
                parts[type] = new Blob([await blob.arrayBuffer()], { type });
            }
        }
        const picture = Object.keys(parts).some((type) => type.startsWith("image/"));
        kept = picture ? parts : null;
    };
    const wrapped = async (items) => {
        await write(items);
        try {
            await remember(items);
        } catch {
            kept = null;
        }
    };
    wrapped.kept = true;
    clip.write = wrapped;
    clip.writeText = async (text) => {
        await writeText(text);
        kept = null;
    };
    clip.read = async () => {
        const found = await read();
        const seen = found.some((item) => item.types.some((type) => type.startsWith("image/")));
        if (seen || !kept) return found;
        const parts = { ...kept };
        for (const item of found)
            for (const type of item.types) if (!parts[type]) parts[type] = item.getType(type);
        return [new ClipboardItem(parts)];
    };
})();"""


@pytest.fixture(scope="session")
def playwright():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright):
    browser = getattr(playwright, BROWSER).launch(headless=not NATIVE)
    yield browser
    browser.close()


@pytest.fixture
def editor(browser, server, playwright):
    """Opens the editor on a sheet of the given blocks, as a new user, and gives its page."""
    contexts = []

    def start(
        *blocks, client=None, more=(), pages=(), theme=None, touch=False, words=None, wait=1100
    ):
        """`more` holds the blocks of a second page. With `touch` the window takes fingers too,
        and with `touch="landscape"` the iPad lies on its side.

        `pages` holds the pages after the first, each a whole page: its blocks and, where it has
        them, its own guides, grid and landscape. `theme` is the one picked on the account page:
        "" opens the panel Seiten, none is Blattform, which starts with that panel shut. `words`
        are the sheet's Lernwörter. `wait` is the time in ms from a change to its save: a test
        that counts on a change being unsaved for a while asks for a teacher's 2000.
        """
        window = {"viewport": {"width": 1400, "height": 1000}, "has_touch": bool(touch)}
        if touch:
            # Fingers mean an iPad, and its own window: 834 by 1194, or on its side.
            window["viewport"] = TURNED if touch == "landscape" else IPAD
        if WEBKIT and touch:
            # In WebKit its sharp screen and its name too.
            window = {**playwright.devices["iPad Pro 11"], "viewport": window["viewport"]}
        context = browser.new_context(**window)
        contexts.append(context)
        # The tests save 1.1 s after a change; a teacher's page waits 2 s (saves.ts). Not less: a
        # test that waits for "Speichert …" looks at most 1 s apart, and must not look past it.
        context.add_init_script(f"window.saveAfter = {wait}")
        # A copy stamps the system clipboard and a paste reads it; headless Chromium asks no one.
        # WebKit knows no leave to write, and lets the page write without one.
        context.grant_permissions(["clipboard-read", *([] if WEBKIT else ["clipboard-write"])])
        if WEBKIT:
            context.add_init_script(READ_PICTURE)
        # The tour would open on the first visit and lie over the sheet.
        context.add_init_script("localStorage.setItem('tour', '1')")
        if theme is not None:
            context.add_init_script(f"localStorage.setItem('theme', {json.dumps(theme)})")
        client = client or user()
        # The session cookie is Secure and this server speaks http, so it goes by hand.
        context.add_cookies(
            [{"name": "session", "value": client.cookies["session"], "url": server}]
        )
        page = context.new_page()
        rest = [*([more] if more else []), *pages]
        page.goto(f"{server}/blatt/{sheet(client, blocks, *rest, words=words)['id']}")
        # The editor listens for keys once the sheet has loaded.
        # The first load of a cold browser takes more than the 5 s of every other wait when the
        # machine has more workers than cores.
        expect(page.locator('main.editor[data-ready="1"]')).to_be_visible(timeout=10000)
        # A thumbnail draws blocks too, with no name.
        count = len(blocks) + len(more) + sum(len(p["blocks"]) for p in pages)
        expect(page.locator(".block[data-id]")).to_have_count(count)
        # A font that comes in late moves what stands in it, and the editor measures anew then. A
        # place read or a click sent before that is not where the text ends up (#419, #436, #504).
        page.evaluate(SETTLED)
        # The editor fits the sheet to the desk as it opens, and the desk's observer may set the
        # width anew a frame later. A place read before then is not where the block ends up.
        page.wait_for_function(MEASURED, timeout=10000)
        # The browser fixture is one browser for the run, and every context shares its clipboard.
        # A picture an earlier test left there would paste into this one (#182).
        page.evaluate("navigator.clipboard.writeText('')")
        return page

    yield start
    # Leaving the editor saves. A save that comes in late finds no such session in the next
    # test's data and changes nothing.
    for context in contexts:
        context.close()
