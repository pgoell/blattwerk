"""The sheet as the editor shows it and as the PDF prints it, and how far the two pictures differ.

screen, printed = screen_and_print(browser, server, client, sheet_id)
assert not over(screen, printed)
"""

import io
from array import array

import httpx
import pypdfium2
from PIL import Image, ImageChops
from PIL.ImageFilter import BoxBlur, MaxFilter, MinFilter
from ui import BROWSER, sheet

# The side of the square around a pixel in which the other picture may have it: one pixel to
# each side. WebKit sets every other row of a text one pixel of the page lower than Chromium,
# which prints, and the pictures are at twice the page's size: two pixels there.
NEAR = 5 if BROWSER == "webkit" else 3

# How far a pixel's red, green or blue may lie apart in the two pictures before it counts. The
# browser and pdfium smooth the edge of a letter each in their own way: that is no difference.
TOLERANCE = 64
# The share of a page's pixels that may differ. A sentence that prints 10 mm lower is 0.006.
# Chromium differs by none for most blocks and by 0.0006 at most, where a Karo runs off the
# page's edge. WebKit draws the screen and Chromium the PDF: rows of a school's script lie up to
# three pixels off there, 0.002 of the page.
LIMIT = 0.004 if BROWSER == "webkit" else 0.0015
# The page's share is blind to a small fault (issue #282): an outline 0.5 mm lower is 0.0025 of
# the page, a hairline that is gone 0.0009, another colour 0. So two measures more, each of the
# page in tiles of 10 mm.
#
# The share of a tile's pixels that differ. In Chromium an outline that prints 0.5 mm lower is
# 0.068 and a word 0.050. A page the tests compare has 0.007 at most, where a Karo runs off the
# page's edge.
# WebKit lays rows of text up to 0.54 mm lower and ends a picture 0.4 mm short (ROWS and EDGE in
# test_pixels.py, what the browsers round): 0.065 in a school's script and 0.062 at a picture's
# right edge. That is more than the 0.059 of that outline and the 0.0045 of that word, so there
# it sees neither. It sees a sentence 1 mm lower, 0.099.
TILE = 0.07 if BROWSER == "webkit" else 0.01
# The share of a tile's ink that only one picture has, where ink is how far a pixel's red, green
# or blue lies below white. It sees a line that is gone, 1, and a colour: #555555 for #222222 is
# 0.25 to 0.27 in a text and a ruling, #ffe066 for #ffd43b 0.28, in both browsers. Chromium has
# 0.196 at most, in a table, where pdfium fills every pixel a line touches. WebKit has 0.224 at
# most, at a box's border of 0.5 mm, so it sees all three colours. CI's Chromium runs on another
# machine's fonts than a laptop's, so its limit leaves more room.
INK = 0.25 if BROWSER == "webkit" else 0.21
# The ink a tile has to hold for all of it to count: a third of a hairline's, 0.3 mm wide and
# dark, through the tile's middle. Less ink than this is measured against this much.
FLOOR = 3
LIMITS = {"page": LIMIT, "tile": TILE, "ink": INK}
# What the editor draws on the page and the PDF does not print: the Karo paper, the guide lines,
# what marks the selection, the hint in an empty text, the page's round corners, and the zoom and
# the page's number that float over the desk's lower edge. The white ring keeps the desk out of
# the last row of pixels, where the page ends within a pixel.
HIDE = """
.sheet { border-radius: 0 !important; background-image: none !important; }
.sheet { box-shadow: 0 0 0 2px #fff !important; outline: none !important; }
.sheet .rule, .sheet .moveable-control-box, .sheet > .bar, .sheet .end { display: none !important; }
.sheet [data-hint] p::before { content: none !important; }
.dock { display: none !important; }
"""
LOADED = """Promise.all([
    document.fonts.ready,
    ...[...document.images].map((img) => img.decode().catch(() => {})),
])"""


def as_png(image):
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def screen_and_print(browser, server, client, sheet_id, page=0):
    """The sheet's page in the editor and the same page of the PDF, each a PNG of one width."""
    session = client.cookies["session"]
    # At twice the size: a ruling's line is 0.2 mm, less than a pixel at one, where the browser
    # draws it pale over two rows and pdfium dark on one.
    window = {"viewport": {"width": 1400, "height": 1400}, "device_scale_factor": 2}
    context = browser.new_context(**window)
    # The tour would lie over the sheet.
    context.add_init_script("localStorage.setItem('tour', '1')")
    # The session cookie is Secure and this server speaks http, so it goes by hand.
    context.add_cookies([{"name": "session", "value": session, "url": server}])
    tab = context.new_page()
    tab.goto(f"{server}/blatt/{sheet_id}")
    tab.locator('main.editor[data-ready="1"]').wait_for()
    tab.add_style_tag(content=HIDE)
    # As the page that is printed does: a picture and a font come in after the blocks are laid out.
    tab.evaluate(LOADED)
    screen = tab.locator(f'.sheet[data-page="{page}"]').screenshot()
    # Before the PDF is asked for: leaving the editor saves.
    context.close()
    cookie = {"Cookie": f"session={session}"}
    res = httpx.get(f"{server}/api/sheets/{sheet_id}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    paper = pypdfium2.PdfDocument(res.content)[page]
    width = Image.open(io.BytesIO(screen)).width
    # pdfium fills every pixel a table's line touches, one more than the line is wide at any
    # size. Drawn twice as large and halved, that is half a pixel.
    large = paper.render(scale=2 * width / paper.get_width()).to_pil()
    return screen, as_png(large.reduce(2))


def beyond(one, two):
    """How far each pixel of `one` lies outside what `two` has at its place and around it."""
    # The editor draws the page a little larger than the PDF's own scale, so a thin line falls
    # on the next pixel in one of the two. A pixel that the other picture has beside it is no
    # difference.
    darkest, lightest = (two.filter(kind(NEAR)) for kind in (MinFilter, MaxFilter))
    return ImageChops.lighter(ImageChops.subtract(one, lightest), ImageChops.subtract(darkest, one))


def tiles(image, grid):
    """The picture's mean around the middle of each tile, row by row."""
    # Made smaller with a triangle as wide as two tiles: each tile weighs its middle most and
    # shares its edge with the next, so a line on the edge of a tile is no difference when it
    # falls a pixel to the other side in one picture.
    return array("f", image.convert("F").resize(grid, Image.Resampling.BILINEAR).tobytes())


def measures(screen, printed):
    """How far the two pictures differ, and a PNG of the screen in pale with what differs in red.

    Each measure by name, with its highest value and where that is: "page", the share of the
    pixels that differ; "tile", that share in the worst tile of 10 mm; "ink", the share of a
    tile's ink that only one picture has, in the worst tile and colour.

    A pixel differs when its red, green or blue lies more than TOLERANCE from all the other
    picture has within a pixel of it. Of two pictures of other sizes the part both have is
    compared: pdfium rounds a page's height its own way.
    """
    first, second = (Image.open(io.BytesIO(data)).convert("RGB") for data in (screen, printed))
    size = min(first.width, second.width), min(first.height, second.height)
    one, two = first.crop((0, 0, *size)), second.crop((0, 0, *size))
    # A ruling's line is a pixel and a half wide even at twice the size. Where it lies between
    # two rows the browser draws both half dark and pdfium one dark and one pale. Each pixel as
    # the mean of the nine around it holds the same ink either way.
    soft, softer = one.filter(BoxBlur(1)), two.filter(BoxBlur(1))
    red, green, blue = ImageChops.lighter(beyond(soft, softer), beyond(softer, soft)).split()
    most = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    off = most.point(lambda v: 255 if v > TOLERANCE else 0)
    pale = Image.blend(one, Image.new("RGB", size, "white"), 0.7)
    pale.paste((255, 0, 0), mask=off)
    # A page of another size or on its side is a difference: what only one picture has counts,
    # once it is more than the pixel or two of pdfium's rounding.
    whole = max(first.width, second.width) * max(first.height, second.height)
    common = size[0] * size[1]
    lost = whole - common if common < 0.99 * whole else 0
    found = {"page": ((off.histogram()[255] + lost) / (common + lost), "")}
    # An A4 page, upright or on its side.
    across = 30 if size[0] > size[1] else 21
    grid = across, max(1, round(across * size[1] / size[0]))

    def where(tile):
        row, column = divmod(tile, across)
        return f" around {column * 10 + 5}, {row * 10 + 5} mm"

    shares = tiles(off, grid)
    worst = max(range(len(shares)), key=shares.__getitem__)
    found["tile"] = shares[worst] / 255, where(worst) if shares[worst] else ""
    found["ink"] = 0.0, ""
    inks = (ImageChops.invert(picture).split() for picture in (one, two))
    for colour, shown, paper in zip(("red", "green", "blue"), *inks, strict=True):
        pairs = zip(tiles(shown, grid), tiles(paper, grid), strict=True)
        for tile, (here, there) in enumerate(pairs):
            part = abs(here - there) / max(here, there, FLOOR)
            if part > found["ink"][0]:
                told = f"{where(tile)}: {colour} {here:.1f} on the screen, {there:.1f} in print"
                found["ink"] = part, told
    return found, as_png(pale)


def diff(screen, printed):
    """The share of the page's pixels that differ, and the PNG that `measures` gives."""
    found, marked = measures(screen, printed)
    return found["page"][0], marked


def grey(browser, server, client, page):
    """The page on the screen and in the PDF, in grey and both of the screen's size."""
    mine = sheet(client, page)["id"]
    screen, printed = (
        Image.open(io.BytesIO(data)).convert("L")
        for data in screen_and_print(browser, server, client, mine)
    )
    # pdfium rounds a page's size up: a pixel more would move every part cut out by a pixel.
    return screen, printed.crop((0, 0, *screen.size))


def dark(image, part, down=True):
    """How dark each row of pixels is, from 0 to 1, in the `part` of an upright page given in mm.

    Each column with `down` off.
    """
    cut = image.crop(tuple(round(v * image.width / 210) for v in part))
    # Each row as the mean of its pixels.
    rows = cut.resize((1, cut.height) if down else (cut.width, 1), Image.Resampling.BOX)
    return [1 - v / 255 for v in rows.tobytes()]


def runs(rows):
    """Each stretch of rows with ink in it: its first row, its darkest and the darkness summed."""
    found, start = [], None
    for i, v in enumerate([*rows, 0]):
        if v > 0.05 and start is None:
            start = i
        elif v <= 0.05 and start is not None:
            found.append((start, max(rows[start:i]), sum(rows[start:i])))
            start = None
    return found


def over(screen, printed):
    """Each measure that is over its limit, told with its number and its place.

    An empty list where the print matches the screen.
    """
    found, _ = measures(screen, printed)
    return [
        f"{name} {value:.4f}, limit {LIMITS[name]}{where}"
        for name, (value, where) in found.items()
        if value >= LIMITS[name]
    ]
