"""The dots and dashes of a border meet where its way round ends, on the screen as in print.

Issue #304: a dot lay over another at the seam. Issue #305: the screen joined a box's first dash
to its last corner.
"""

import math
import statistics
from itertools import pairwise

import pytest
from pixels import LIMITS, dark, grey, measures, screen_and_print
from playwright.sync_api import expect
from ui import BROWSER, RECT, TEXT, at, box, sheet, user

# How dark a border of #222222 is, from 0 to 1.
BLACK = 1 - 0x22 / 255
WIDTHS = [0.25, 0.5, 1, 3]
LOOKS = [(width, dash) for dash in ("dashed", "dotted") for width in WIDTHS]
W, H = 60, 30
# How far a dot or a dash may lie from its place, in mm: a pixel of the picture is 0.13 mm.
NEAR = 0.15
# How far a whole block may lie along on the screen from where it prints, in mm. WebKit lays a
# block out on a whole pixel of the page, 0.26 mm: it had 0.28 at most, Chromium 0.13.
SHIFT = 0.3 if BROWSER == "webkit" else 0.2
# How far a mark round a triangle or a star may lie from its place, measured along its way round.
# A block that lies a pixel off in the picture has its marks off by that much one way on one side
# and the other way on the next. In print a block at the page's right edge had 0.28.
ROUND = SHIFT + 0.1
# The share of its ink a dot or a dash may hold more or less than the others.
UNEVEN = 0.2
# The ink a corner may hold more or less on the screen than in print, in mm², whatever the stroke.
CORNER = 0.04


# The kinds with a top edge to measure along, and the two that have none: their own page, since
# one page has no room for seven kinds turned.
BOXES = ["rect", "rounded", "circle", "bubble", "text"]
POINTS = ["triangle", "star"]
PAGES = pytest.mark.parametrize("names", [BOXES, POINTS], ids=["boxes", "points"])


def page(width, dash, names=BOXES):
    """Each kind that takes a border: level, in a group, and turned by a right angle."""
    edge = {"stroke": "#222222", "strokeWidth": width, "dash": dash}
    kinds = {
        "rect": ("shape", {**RECT, **edge}),
        "rounded": ("shape", {**RECT, **edge, "kind": "rounded"}),
        "circle": ("shape", {**RECT, **edge, "kind": "circle"}),
        "bubble": ("shape", {**RECT, **edge, "kind": "bubble"}),
        "text": ("text", {**TEXT, **edge}),
        "triangle": ("shape", {**RECT, **edge, "kind": "triangle"}),
        "star": ("shape", {**RECT, **edge, "kind": "star"}),
    }
    level = [(8, 10), (75, 10), (142, 10), (8, 48), (75, 48)]
    grouped = [(142, 48), (8, 86), (75, 86), (142, 86), (8, 124)]
    if names is POINTS:
        # Clear of the page's right edge: a picture is a pixel wider or narrower than the page,
        # which lays a mark there up to 0.13 mm along a slanted side.
        grouped = level[3:]
    # Turned about its middle a block stands 30 mm wide and 60 high.
    turned = [(35 * i, 185) for i in range(5)]
    blocks = []
    places = zip(((name, kinds[name]) for name in names), level, grouped, turned, strict=False)
    for (name, (kind, props)), one, two, three in places:
        blocks += [
            box(name, kind, props, x=one[0], y=one[1], w=W, h=H),
            box(f"{name} in a group", kind, props, x=two[0], y=two[1], w=W, h=H, group=["g"]),
            box(f"{name} turned", kind, props, x=three[0], y=three[1], w=W, h=H, angle=90),
        ]
    return blocks


def kind_of(block):
    return block["props"].get("kind", "rect")


def seam(block, width):
    """Where the way round starts and ends, along the top edge from the box's left."""
    starts = {"rect": width / 2, "rounded": 4, "bubble": 4 + width / 2, "circle": W / 2}
    return starts[kind_of(block)]


def on_page(block, part):
    """A part of the block's own box, from its corner, as the part of the page it lies on."""
    left, top, right, low = part
    x, y = block["x"], block["y"]
    if block.get("angle") != 90:
        return (x + left, y + top, x + right, y + low)
    # Turned about its middle, the top edge is the right one and runs down.
    edge, start = x + W / 2 + H / 2, y + H / 2 - W / 2
    return (edge - low, start + left, edge - top, start + right)


def area(picture, block, part):
    """The ink in a part of the block's box, as mm² of the border's colour."""
    place = on_page(block, part)
    mm = picture.width / 210
    rows = dark(picture, place)
    across = round(place[2] * mm) - round(place[0] * mm)
    return sum(rows) * across / BLACK / mm**2


def marks(picture, block, part):
    """Each dot or dash along the top edge in a part of the block's box: its middle from the
    part's start in mm, and its ink in mm². One cut by the part's end is left out."""
    place = on_page(block, part)
    level = block.get("angle") != 90
    mm = picture.width / 210
    deep = round(place[3 if level else 2] * mm) - round(place[1 if level else 0] * mm)
    # The ink of each column of pixels, in pixels: a mean would lose a small dot in a deep strip.
    cols = [v * deep for v in dark(picture, place, down=not level)]
    return [
        (middle / mm, ink / BLACK / mm**2)
        for start, end, middle, ink in lumps(cols)
        if start > 0 and end < len(cols)
    ]


def lumps(cols):
    """Each stretch of columns with ink: its first column, the one after its last, its middle and
    its ink."""
    found, start = [], None
    for i, v in enumerate([*cols, 0]):
        if v > 0.15 and start is None:
            start = i
        elif v <= 0.15 and start is not None:
            ink = sum(cols[start:i])
            middle = sum(j * cols[j] for j in range(start, i)) / ink
            found.append((start, i, middle, ink))
            start = None
    return found


def way(block, width):
    """The middle of a triangle's or a star's stroke as points of its box: OUTLINES in sheet.tsx."""
    e = width / 2
    if kind_of(block) == "triangle":
        return [(W / 2, e), (W - e, H - e), (e, H - e)]
    spikes = [(0.38 if i % 2 else 1, i * math.pi / 5) for i in range(10)]
    return [
        (
            e + (W - 2 * e) * (0.5 + r * math.sin(a) / 1.902),
            e + (H - 2 * e) * (1 - r * math.cos(a)) / 1.809,
        )
        for r, a in spikes
    ]


def length(points):
    return sum(math.dist(a, b) for a, b in pairwise([*points, points[0]]))


def along(points, x, y):
    """How far along the way round the point of it nearest to a place lies, in mm."""
    best, start = (math.inf, 0), 0
    for (ax, ay), (bx, by) in pairwise([*points, points[0]]):
        dx, dy, side = bx - ax, by - ay, math.dist((ax, ay), (bx, by))
        t = min(1, max(0, ((x - ax) * dx + (y - ay) * dy) / side**2))
        best = min(best, (math.hypot(x - ax - t * dx, y - ay - t * dy), start + t * side))
        start += side
    return best[1]


def marks_around(picture, block, width):
    """Each dot or dash of a triangle or a star, all the way round: where it starts and ends
    along the way in mm, and its ink in mm². No edge of theirs is level and the way ends on a
    corner, so no strip holds the seam."""
    points = way(block, width)
    whole = length(points)
    mm = picture.width / 210
    left, top, right, low = (round(v * mm) for v in on_page(block, (-0.5, -0.5, W + 0.5, H + 0.5)))
    cut = picture.crop((left, top, right, low))
    # The ink of each pixel of the way's length: a pixel counts for the place on the way it lies
    # nearest to.
    cols = [0.0] * math.ceil(whole * mm)
    for i, v in enumerate(cut.tobytes()):
        if v < 255:
            row, col = divmod(i, cut.width)
            x, y = (left + col + 0.5) / mm - block["x"], (top + row + 0.5) / mm - block["y"]
            if block.get("angle") == 90:
                # Turned about its middle: `on_page` the other way.
                x, y = y + W / 2 - H / 2, W / 2 + H / 2 - x
            cols[int(along(points, x, y) * mm) % len(cols)] += 1 - v / 255
    # From the emptiest place on, so that the way's end cuts no mark.
    gap = min(range(len(cols)), key=cols.__getitem__)
    cols = cols[gap:] + cols[:gap]
    # With the pale pixel before and after: a dot of 0.25 mm is two pixels wide, and on a slant
    # a fourth of its ink may lie in those.
    return sorted(
        (
            *((gap + v) / mm % whole for v in (start, end, middle + 0.5)),
            sum(cols[max(0, start - 1) : end + 1]) / BLACK / mm**2,
        )
        for start, end, middle, _ in lumps(cols)
    )


def fitted(found, points, width):
    """What is wrong with the dots or dashes round a triangle or a star, and where those start
    that lie clear of its corners.

    At a corner the stroke lies over itself, the more the sharper it is: a dash bent round one
    holds less ink, and two dots to either side touch. So the marks between the corners are
    measured: each holds as much ink as the others, and each starts and ends a whole number of
    steps from the others, of which a whole number goes round. Dashes that are not fitted to the
    way round drift off those steps, wherever the way starts.
    """
    ring = length(points)

    def apart(a, b, span=ring):
        return (a - b + span / 2) % span - span / 2

    # How far from each corner the stroke lies over itself, half its width by how sharp it turns,
    # and as much again: the screen joins two dashes that near each other at a star's side tip.
    corners, at = [], 0
    for i, here in enumerate(points):
        (ax, ay), (bx, by) = (
            (b[0] - a[0], b[1] - a[1])
            for a, b in ((points[i - 1], here), (here, points[(i + 1) % len(points)]))
        )
        turn = math.atan2(ax * by - ay * bx, ax * bx + ay * by)
        corners.append((at, width * math.tan(abs(turn) / 2) + 0.3))
        at += math.hypot(bx, by)

    def clear(at):
        return all(abs(apart(at, corner)) > reach for corner, reach in corners)

    whole = [(at, ink) for start, end, at, ink in found if clear(start) and clear(end)]
    if not found:
        return ["none found"], []
    # A wide dash is as long as a star's side: none may lie clear of the corners.
    ink = statistics.median([ink for _, ink in whole] or [1])
    faults = [
        f"ink {v:.3f} for {ink:.3f} at {at:.2f}" for at, v in whole if abs(v / ink - 1) > UNEVEN
    ]

    def off(count):
        """How far each mark lies off the steps, of which `count` go round."""
        each = [apart(at, whole[0][0], ring / count) for at, _ in whole]
        # About the middle one: the first may be the one that is off.
        middle = statistics.median(each or [0])
        return [apart(v, middle, ring / count) for v in each]

    # A pixel is too coarse to count the steps by one step's length: the count that fits best.
    about = round(ring / statistics.median([b[2] - a[2] for a, b in pairwise(found)] or [ring]))
    count = min(range(max(1, about - 3), about + 4), key=lambda n: sum(abs(v) for v in off(n)))
    faults += [
        f"{v:.2f} off the {count} steps at {at:.2f}"
        for v, (at, _) in zip(off(count), whole, strict=True)
        if abs(v) > ROUND
    ]
    return faults, whole


def edge_part(block, width, dash):
    """The top edge with the seam on it, clear of the corner the way round turns next."""
    start = seam(block, width)
    if kind_of(block) == "circle":
        # A circle's edge falls away from its top: the dot at the seam and one to each side.
        return (start - 3.4 * width, -0.5, start + 3.4 * width, width + 1)
    corner = 0 if kind_of(block) == "rect" else 4
    return (start - 1.3 * width - 0.3, -0.5, W - corner - 1.3 * width, 1.4 * width)


def spots(block, width):
    """The squares to compare ink in: the box's four corners and the seam."""
    side = width + 0.3
    if kind_of(block) in POINTS:
        # Each point of the way round: it starts and ends on one of them.
        return {
            f"point {i}": (x - side, y - side, x + side, y + side)
            for i, (x, y) in enumerate(way(block, width))
        }
    start = seam(block, width)
    return {
        "top left": (-0.3, -0.3, side, side),
        "top right": (W - side, -0.3, W + 0.3, side),
        "low right": (W - side, H - side, W + 0.3, H + 0.3),
        "low left": (-0.3, H - side, side, H + 0.3),
        "seam": (start - side, -0.3, start + side, side),
    }


def uneven(found):
    """What is wrong with the dots or dashes: each holds as much ink as the others and stands as
    far from the next. A dot with another over it holds more, a stub less."""
    if not found:
        return ["none found"]
    ink = statistics.median(ink for _, ink in found)
    gaps = [b[0] - a[0] for a, b in pairwise(found)]
    gap = statistics.median(gaps or [0])
    heavy = [
        f"ink {v:.3f} for {ink:.3f} at {at:.2f}" for at, v in found if abs(v / ink - 1) > UNEVEN
    ]
    return heavy + [
        f"gap {v:.2f} for {gap:.2f} after {at:.2f}"
        for (at, _), v in zip(found, gaps, strict=False)
        if abs(v - gap) > NEAR
    ]


def meeting(screen, printed, blocks, width, dash):
    """Each block whose dots or dashes do not meet in print, or lie elsewhere on the screen."""
    faults = []
    for block in blocks:
        if kind_of(block) == "circle" and dash == "dashed":
            # Its dashes lie too far apart for a strip along its top: `spots` sees its seam.
            continue
        ring = length(way(block, width)) if kind_of(block) in POINTS else 0
        if ring:
            # All the way round there is no end to cut a mark.
            found = [marks_around(p, block, width) for p in (printed, screen)]
            (wrong, on_paper), (odd, _) = (fitted(each, way(block, width), width) for each in found)
            # A mark at the edge of a corner's reach may count as clear of it in one picture alone.
            shown = [mark[2:] for mark in found[1]]
            lone, last = -1, ring
        else:
            part = edge_part(block, width, dash)
            lone = 0.5 + width * (4.5 if dash == "dashed" else 1.5)
            on_paper, shown = marks(printed, block, part), marks(screen, block, part)
            wrong, odd = uneven(on_paper), uneven(shown)
            last = part[2] - part[0] - lone
        faults += [f"{block['id']} in print: {fault}" for fault in wrong]
        faults += [f"{block['id']} on the screen: {fault}" for fault in odd]
        # Each mark in print with the one nearest to it on the screen. The part's end may cut a
        # mark in one picture alone, so one within a dash's length of an end need not have its twin.
        span = ring or 1e9
        nearest = (
            min(((a - b + span / 2) % span - span / 2 for b, _ in shown), key=abs, default=99)
            for a, _ in on_paper
        )
        off = list(nearest)
        inner = [v for v, (a, _) in zip(off, on_paper, strict=True) if lone < a < last]
        lost = 0 if ring else len(shown) - sum(abs(v) < SHIFT + NEAR for v in off)
        # A turned block lies up to a pixel of the screen further along than it prints, all of it.
        shift = statistics.median(inner or [0])
        near = ROUND if ring else NEAR
        if abs(shift) > SHIFT or any(abs(v - shift) > near for v in inner) or lost > 1:
            far = max(inner, key=lambda v: abs(v - shift), default=0)
            told = f"the print {shift:.2f} mm along, one mark {far:.2f}, {lost} only on the screen"
            faults.append(f"{block['id']}: {told}")
    return faults


def corners(screen, printed, blocks, width):
    """Each corner and seam where the screen holds more or less ink than the print."""
    # The square the screen had too much was 0.28 of the stroke's width squared. A dash that
    # crosses the square's edge lies up to a pixel along in one picture: its width by 0.13 mm.
    limit = 0.12 * width**2 + 0.04 * width + CORNER
    faults = []
    for block in blocks:
        # A turned block lies up to a pixel of the screen further along than it prints, and in
        # WebKit any block up to a pixel of the page, either way. So the square that fits best:
        # in WebKit that hides the fault below a stroke of 3 mm.
        along = (-0.13, 0, 0.13) if block.get("angle") else (0,)
        slides = [(x, 0) for x in along]
        if BROWSER == "webkit":
            slides = [(x * 0.13, y * 0.13) for x in range(-2, 3) for y in range(-2, 3)]
        for name, (left, top, right, low) in spots(block, width).items():
            on_paper = area(printed, block, (left, top, right, low))
            inks = [area(screen, block, (left + x, top + y, right + x, low + y)) for x, y in slides]
            shown = min(inks, key=lambda ink: abs(ink - on_paper))
            if abs(shown - on_paper) > limit:
                told = f"{shown:.3f} mm² on the screen, {on_paper:.3f} in print, limit {limit:.3f}"
                faults.append(f"{block['id']} {name}: {told}")
    return faults


@PAGES
@pytest.mark.parametrize("width, dash", LOOKS)
def test_the_dots_and_dashes_of_a_border_meet_in_print_as_on_the_screen(
    browser, server, width, dash, names
):
    """A1, A2, I1: no dot lies over another at the seam, and no dash is a stub."""
    blocks = page(width, dash, names)
    screen, printed = grey(browser, server, user(), blocks)
    assert not meeting(screen, printed, blocks, width, dash)


@PAGES
@pytest.mark.parametrize("width, dash", LOOKS)
def test_the_screen_draws_the_corners_and_the_seam_as_the_print_does(
    browser, server, width, dash, names
):
    """A4, I1: the screen filled the corner a box's dashes start at with a square of stroke."""
    blocks = page(width, dash, names)
    screen, printed = grey(browser, server, user(), blocks)
    assert not corners(screen, printed, blocks, width)


def test_the_corner_of_a_wide_dashed_box_is_on_the_screen_as_it_prints(browser, server):
    """A5: the sheet of issue #305."""
    client = user()
    props = {**RECT, "strokeWidth": 3, "dash": "dashed"}
    mine = sheet(client, [box("a", "shape", props, x=45, y=170, w=120, h=30)])["id"]
    found, _ = measures(*screen_and_print(browser, server, client, mine))
    assert found["ink"][0] < LIMITS["ink"], found


def test_a_box_no_larger_than_two_strokes_keeps_its_border(editor):
    """I7: there is no room for drawn dashes."""
    props = {**RECT, "strokeWidth": 3, "dash": "dashed"}
    page = editor(box("a", "shape", props, x=40, y=60, w=6, h=6))
    frame = at(page, "a").locator(".frame")
    expect(frame).to_have_css("border-top-style", "dashed")
    expect(frame.locator("svg")).to_have_count(0)


@pytest.mark.parametrize("kind", POINTS)
@pytest.mark.parametrize("dash", ["dashed", "dotted"])
def test_a_triangle_and_a_star_no_larger_than_two_strokes_keep_their_border(editor, kind, dash):
    """I6: one dash or dot goes round at least."""
    props = {**RECT, "kind": kind, "strokeWidth": 3, "dash": dash}
    page = editor(box("a", "shape", props, x=40, y=60, w=6, h=6))
    path = at(page, "a").locator("svg.outline path")
    expect(path).to_have_attribute("stroke", "#222222")
    expect(path).to_have_attribute("stroke-width", "3")
    drawn = "(a) => a.getTotalLength() / a.getAttribute('stroke-dasharray').split(' ')[1]"
    # The way round is at least as long as from one mark to the next: a mark lies on it.
    assert path.evaluate(drawn) >= 1


@pytest.mark.parametrize("kind", POINTS)
@pytest.mark.parametrize("dash", ["dashed", "dotted"])
def test_a_dashed_triangle_and_star_keep_their_fill(editor, kind, dash):
    """I2: the dashes are drawn as the outline was, with its fill and how far that shows through."""
    props = {**RECT, "kind": kind, "fill": "#ffd43b", "opacity": 0.5, "dash": dash}
    page = editor(box("a", "shape", props, x=40, y=60, w=60, h=30))
    path = at(page, "a").locator("svg.outline path")
    expect(path).to_have_attribute("fill", "#ffd43b")
    expect(path).to_have_attribute("fill-opacity", "0.5")
