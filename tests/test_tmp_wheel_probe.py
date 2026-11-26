"""Temporary: what CI's Chromium sees in test_a_plain_wheel_scrolls_under_the_hand. Goes before the merge."""

from test_zoom import wheel
from test_zoom_hand import HAND
from ui import TEXT, box, expect

SEE = """() => {
    const d = document.querySelector('.desk'), l = document.querySelector('.left');
    const r = d.getBoundingClientRect();
    const at = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
    return {top: d.scrollTop, max: d.scrollHeight - d.clientHeight, desk: [r.x, r.y, r.width, r.height],
        left: [l.scrollTop, l.scrollHeight, l.clientHeight, l.offsetWidth, l.clientWidth],
        doc: [document.scrollingElement.scrollTop, document.scrollingElement.scrollHeight, innerHeight],
        at: at && (at.className || at.tagName) + '', hands: document.querySelectorAll('.hand').length,
        focus: document.activeElement.tagName + '.' + document.activeElement.className,
        wheels: window.seenWheels};
}"""


def test_tmp_probe(editor):
    page = editor(box("a", "text", TEXT))
    page.evaluate(
        "() => { window.seenWheels = []; addEventListener('wheel', (e) => window.seenWheels.push([e.deltaY, e.target.className + '', e.defaultPrevented, Math.round(e.clientX), Math.round(e.clientY)]), true); }"
    )
    out = [page.evaluate(SEE)]
    page.keyboard.down("Space")
    expect(page.locator(HAND)).to_have_count(1)
    for delta in (100, 200, -300):
        wheel(page, delta, ctrl=False)
        page.wait_for_timeout(700)
        out.append(page.evaluate(SEE))
    raise AssertionError(out)
