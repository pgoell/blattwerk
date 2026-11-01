"""Keys the teacher tool sends.

Playwright knows the US layout only. ``keyboard.press`` of Ä raises "Unknown key", and
``keyboard.type`` sends Ü, ä, ö and ß as insertText with no keydown. A picked block holds
no editable focus, so that text reaches nothing and the letter is lost (#617).
"""

from playwright.sync_api import Page
from teacher_page_name import press
from teacher_page_ns import g

# What Playwright's US layout presses. ``\n`` and ``\r`` are Enter.
US = frozenset(
    " \n\r`1234567890-=qwertyuiop[]\\asdfghjkl;'zxcvbnm,./"
    '~!@#$%^&*()_+QWERTYUIOP{}|ASDFGHJKL:"ZXCVBNM<>?'
)


def _strike(session, char: str) -> None:
    """One letter as a keydown that carries it, then the keyup."""
    session.send(
        "Input.dispatchKeyEvent",
        {"type": "keyDown", "key": char, "text": char, "unmodifiedText": char},
    )
    session.send("Input.dispatchKeyEvent", {"type": "keyUp", "key": char})


def press_key(page: Page, keys: str) -> None:
    """One press. Plus is the German key. Any other letter outside the US layout is a keydown."""
    if len(keys) == 1 and keys not in US:
        session = page.context.new_cdp_session(page)
        try:
            _strike(session, keys)
        finally:
            session.detach()
        return
    press(page, keys)


def type_text(page: Page, text: str) -> None:
    """Types text. A letter outside the US layout is a keydown, so a picked block opens on it."""
    buf: list[str] = []
    session = None

    def flush() -> None:
        if buf:
            page.keyboard.type("".join(buf))
            buf.clear()

    try:
        for char in text:
            # A tab is not a layout key: Playwright inserts it, as it did before.
            if char in US or char == "\t":
                buf.append(char)
            else:
                flush()
                if session is None:
                    session = page.context.new_cdp_session(page)
                _strike(session, char)
        flush()
    finally:
        if session is not None:
            session.detach()


def key(page: Page, keys: str, times: str = "1") -> str:
    for _ in range(g("number")(times)):
        press_key(page, keys)
    return g("shown")(page, f"pressed {keys} {times} times")


def type_(page: Page, text: str) -> str:
    type_text(page, text)
    return g("shown")(page, f"typed {len(text)} letters")
