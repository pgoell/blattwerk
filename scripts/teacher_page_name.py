"""A name the teacher-page tool resolves past the words on the page.

`one` is the button a little page repeats. `read_value` is a heading's lit button, such as
Übertrag. `press` sends `+` as the German plus key, code BracketRight. Playwright's own `+`
is the US equals key.
"""

from playwright.sync_api import Error, Page
from teacher_page_ns import g

# Modifiers Playwright spells, as bits of a Chrome key event.
MODIFIERS = {"Control": 2, "Shift": 8, "Alt": 1, "Meta": 4}
# The button under a heading that is on: its class, or aria-pressed.
LIT = """(name) => {
    const heads = [...document.querySelectorAll("h2")].filter((h) => h.textContent.trim() === name);
    if (heads.length !== 1) return null;
    const seg = heads[0].nextElementSibling;
    if (!seg || !seg.classList.contains("seg")) return null;
    const on = [...seg.querySelectorAll("button")].filter((b) =>
        b.classList.contains("on") || b.getAttribute("aria-pressed") === "true");
    return on.length ? on.map((b) => b.textContent.trim()).join(", ") : null;
}"""


def one(page: Page, name: str, found):
    """The one button, link, menu item or tab of this exact name, or nothing where several match."""
    locator = page.get_by_role("button", name=name, exact=True)
    for role in ("link", "menuitem", "tab"):
        locator = locator.or_(page.get_by_role(role, name=name, exact=True))
    handles = [item.element_handle() for item in locator.filter(visible=True).all()]
    handles = [el for el in handles if el is not None]
    if len(handles) != 1:
        return None
    el = handles[0]
    box = el.bounding_box()
    if not box:
        return None
    return found(
        round(box["x"] + box["width"] / 2),
        round(box["y"] + box["height"] / 2),
        name,
        True,
        el,
    )


def read_value(page: Page, name: str) -> str:
    """What the field holds, or the lit button under the one heading of that name."""
    found = page.get_by_label(name, exact=True).filter(visible=True)
    if found.count() == 1:
        try:
            return f"{name} is {found.input_value(timeout=3000)}"
        except Error:
            pass
    group = page.evaluate(LIT, name)
    if group is not None:
        return f"{name} is {group}"
    raise g("Refused")(f'no field on the page is called "{name}"')


def _plus(keys: str) -> list[str] | None:
    """The modifiers of a German plus, or nothing when `keys` is another chord."""
    if keys == "+":
        return []
    if not keys.endswith("++"):
        return None
    head = keys[:-2]
    parts = head.split("+") if head else []
    if any(part not in MODIFIERS for part in parts):
        return None
    return parts


def press(page: Page, keys: str) -> None:
    """Presses `keys`. A plus is the German key, code BracketRight, not the US equals key."""
    mods = _plus(keys)
    if mods is None:
        page.keyboard.press(keys)
        return
    bits = 0
    for name in mods:
        bits |= MODIFIERS[name]
    session = page.context.new_cdp_session(page)
    try:
        common = {
            "key": "+",
            "code": "BracketRight",
            "windowsVirtualKeyCode": 221,
            "modifiers": bits,
        }
        down = {**common, "type": "keyDown"}
        # With no modifier the key types +. With Control it zooms and types nothing.
        if bits == 0:
            down["text"] = "+"
            down["unmodifiedText"] = "+"
        session.send("Input.dispatchKeyEvent", down)
        session.send("Input.dispatchKeyEvent", {**common, "type": "keyUp"})
    finally:
        session.detach()
