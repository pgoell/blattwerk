"""The sheet as the editor shows it and as the PDF prints it, and how far the two pictures differ.

screen, printed = screen_and_print(browser, server, client, sheet_id)
share, marked = diff(screen, printed)
assert share < LIMIT
"""

import io

import httpx
import pypdfium2
from PIL import Image, ImageChops
from PIL.ImageFilter import BoxBlur, MaxFilter, MinFilter
from ui import BROWSER

# The side of the square around a pixel in which the other picture may have it: one pixel to
# each side. WebKit sets every other row of a text one pixel of the page lower than Chromium,
# which prints, and the pictures are at twice the page's size: two pixels there.
NEAR = 5 if BROWSER == "webkit" else 3

# How far a pixel's red, green or blue may lie apart in the two pictures before it counts. The
# browser and pdfium smooth the edge of a letter each in their own way: that is no difference.
TOLERANCE = 64
# The share of a page's pixels that may differ. A sentence that prints 10 mm lower is 0.006.
# Chromium differs by none for most blocks and by 0.0005 at most, where a Karo runs off the
# page's edge. WebKit draws the screen and Chromium the PDF: rows of a school's script lie up to
# three pixels off there, 0.002 of the page.
LIMIT = 0.004 if BROWSER == "webkit" else 0.0015
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


def diff(screen, printed):
    """The share of the pixels that differ, and a PNG of the screen in pale with those in red.

    A pixel differs when its red, green or blue lies more than TOLERANCE from all the other
    picture has within a pixel of it. Of two pictures of other sizes the part both have is
    compared: pdfium rounds a page's height its own way.
    """
    one, two = (Image.open(io.BytesIO(data)).convert("RGB") for data in (screen, printed))
    size = min(one.width, two.width), min(one.height, two.height)
    one, two = one.crop((0, 0, *size)), two.crop((0, 0, *size))
    # A ruling's line is a pixel and a half wide even at twice the size. Where it lies between
    # two rows the browser draws both half dark and pdfium one dark and one pale. Each pixel as
    # the mean of the nine around it holds the same ink either way.
    soft, softer = one.filter(BoxBlur(1)), two.filter(BoxBlur(1))
    red, green, blue = ImageChops.lighter(beyond(soft, softer), beyond(softer, soft)).split()
    most = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    off = most.point(lambda v: 255 if v > TOLERANCE else 0)
    pale = Image.blend(one, Image.new("RGB", size, "white"), 0.7)
    pale.paste((255, 0, 0), mask=off)
    return off.histogram()[255] / (size[0] * size[1]), as_png(pale)
