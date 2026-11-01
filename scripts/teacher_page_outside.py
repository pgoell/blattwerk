"""What the window cannot do with a plain click: another app, a web page, a finger, a microphone.

Ctrl-click, a still finger, a Word paste, a picture dragged off a web page, and a microphone
the browser does not have. The brief in docs/teacher-run/rules.md names each verb.
"""

import base64
import html
import re
import time

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as Late
from teacher_page_ns import g

# Long enough that a hold of 500 ms has opened, and short of a teacher's patience.
HOLD = 0.7
MARK = re.compile(r"(\*[^*]+\*|_[^_]+_)")
KINDS = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".gif": "gif", ".webp": "webp"}

# The form reads the microphone when Aufnahme starten is pressed, so this has to be in place first.
# A real device is not there: the clip is a stand-in, and shutting the form still stops the track.
MIC = """(() => {
  if (window.__blattwerkMic) return;
  window.__blattwerkMic = true;
  window.__tracks = window.__tracks || [];
  const mic = async () => {
    const track = { stopped: false, stop() { this.stopped = true; } };
    window.__tracks.push(track);
    return { getTracks: () => [track] };
  };
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia: mic },
  });
  window.MediaRecorder = class {
    static isTypeSupported() { return true; }
    constructor(_stream, options) {
      this.mimeType = (options && options.mimeType) || "audio/webm";
      this.state = "inactive";
    }
    start() { this.state = "recording"; }
    stop() {
      this.state = "inactive";
      setTimeout(() => {
        if (this.ondataavailable) this.ondataavailable({ data: new Blob(["x"]) });
        if (this.onstop) this.onstop();
      }, 0);
    }
  };
})()"""

# Onto the sheet, or into the text that is open. The same event the paste tests send.
PASTE = """([html, text]) => {
  const data = new DataTransfer();
  data.setData("text/plain", text);
  data.setData("text/html", html);
  const init = { clipboardData: data, bubbles: true, cancelable: true };
  const field = document.activeElement;
  const open = field instanceof Element && field.matches(".sheet .ProseMirror, .sheet textarea");
  (open ? field : document.body).dispatchEvent(new ClipboardEvent("paste", init));
}"""

# A picture leaving a web page: its address and an img, and no file. The page stores a data:
# address and refuses one it would have to fetch.
DROP = """([x, y, src]) => {
  const dataTransfer = new DataTransfer();
  dataTransfer.setData("text/uri-list", src);
  dataTransfer.setData("text/html", '<img src="' + src + '" alt="">');
  const under = document.elementFromPoint(x, y);
  if (!under) return false;
  const init = { dataTransfer, clientX: x, clientY: y, bubbles: true, cancelable: true };
  for (const kind of ["dragover", "drop"]) under.dispatchEvent(new DragEvent(kind, init));
  return true;
}"""


def ctrl_click(page: Page, target: str) -> str:
    """Ctrl held, then a click. On a thumbnail that adds the page or drops it."""
    x, y = g("point")(page, target)
    grey = g("greyed")(page, x, y)
    page.keyboard.down("Control")
    try:
        page.mouse.click(x, y)
    finally:
        page.keyboard.up("Control")
    return g("shown")(page, f"ctrl-clicked at {x:g},{y:g}{grey}")


def finger(page: Page, target: str) -> str:
    """A finger held still, then lifted. The menu opens on the lift."""
    x, y = g("point")(page, target)
    session = page.context.new_cdp_session(page)
    try:
        session.send(
            "Input.dispatchTouchEvent",
            {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]},
        )
        time.sleep(HOLD)
        session.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    finally:
        session.detach()
    return g("shown")(page, f"held a finger at {x:g},{y:g}")


def mic(page: Page) -> str:
    """Gives this page a microphone, and each page the window opens after it."""
    page.context.add_init_script(MIC)
    page.evaluate(MIC)
    return g("shown")(page, "the window has a microphone. The MCP page has none: record here")


def _adorn(line: str) -> str:
    out = []
    for part in MARK.split(line):
        if len(part) > 2 and part[0] == part[-1] == "*":
            out.append("<b>" + html.escape(part[1:-1]) + "</b>")
        elif len(part) > 2 and part[0] == part[-1] == "_":
            out.append("<i>" + html.escape(part[1:-1]) + "</i>")
        else:
            out.append(html.escape(part))
    return "".join(out)


def _plain(line: str) -> str:
    return MARK.sub(lambda hit: hit.group(0)[1:-1], line)


def _word(text: str) -> tuple[str, str]:
    """Word's HTML for the marks the brief names, and the words with the marks taken out."""
    parts: list[str] = []
    words: list[str] = []
    for line in text.replace("\\n", "\n").split("\n"):
        bullet = re.fullmatch(r"- (.+)", line)
        number = re.fullmatch(r"\d+\. (.+)", line)
        if line == "":
            parts.append("<p><br></p>")
            words.append("")
            continue
        body = bullet.group(1) if bullet else number.group(1) if number else line
        inner = _adorn(body)
        if bullet:
            parts.append(
                '<p class="MsoListParagraph" style="mso-list:l0 level1 lfo1">'
                '<span style="mso-list:Ignore">-&nbsp;</span>' + inner + "</p>"
            )
        elif number:
            parts.append(
                '<p class="MsoListParagraph" style="mso-list:l0 level1 lfo1">'
                '<span style="mso-list:Ignore">1.&nbsp;</span>' + inner + "</p>"
            )
        else:
            parts.append(f'<p class="MsoNormal">{inner}</p>')
        words.append(_plain(body))
    return "".join(parts), "\n".join(words)


def paste_word(page: Page, text: str) -> str:
    """Pastes text as a Word copy: bold, italic and lists, and nothing else."""
    if not text.strip():
        raise g("Refused")('paste-word takes the words: paste-word "Ein *fett* Wort"')
    marked, words = _word(text)
    page.evaluate(PASTE, [marked, words])
    return g("shown")(page, f'pasted from Word: "{words.replace("\n", " / ")}"')


def _src(what: str) -> tuple[str, str]:
    """The address a web page would hand over, and the words the verb prints."""
    if what.startswith(("https://", "http://")):
        if any(c in what for c in '"<>'):
            raise g("Refused")("a web address cannot hold a quote or a tag")
        return what, "a web address, and the page fetches nothing"
    path = (g("STATE") / what).resolve()
    root = g("STATE").resolve()
    if not path.is_relative_to(root):
        raise g("Refused")(
            f'"{what}" is outside the run folder {root}: only its files can be dropped'
        )
    if not path.is_file():
        raise g("Refused")(f'there is no file "{what}" in {root}')
    kind = KINDS.get(path.suffix.lower())
    if not kind:
        raise g("Refused")("a web picture is a png, jpeg, gif or webp")
    data = base64.b64encode(path.read_bytes()).decode()
    return f"data:image/{kind};base64,{data}", f"{path.name} as a web picture"


def drop_web(page: Page, what: str, target: str) -> str:
    """Drops a picture the way a web page does: the file's bytes, or an address and no fetch."""
    src, note = _src(what)
    x, y = g("point")(page, target)
    if not page.evaluate(DROP, [x, y, src]):
        raise g("Refused")(f"nothing is under {x:g},{y:g}")
    if src.startswith("http"):
        try:
            page.locator(".notice.fault").wait_for(timeout=3000)
        except Late:
            raise g("Refused")(
                "the page did not say that a web address cannot be dropped"
            ) from None
    return g("shown")(page, f"dropped {note} at {x:g},{y:g}")
