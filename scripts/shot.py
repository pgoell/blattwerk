"""A sheet as the editor shows it and as the PDF prints it, each as a PNG.

    mise run shot -- pages.json out/

pages.json holds the pages of the sheet, each a list of blocks. Writes screen.png and pdf.png.
"""

import json
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import httpx
import pypdfium2
from playwright.sync_api import sync_playwright

from blattwerk import db

sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))
import ui  # ty: ignore[unresolved-import]

pages = json.loads(Path(sys.argv[1]).read_text())
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
screen, printed = out / "screen.png", out / "pdf.png"
# Before the first user: the database is made where this points.
db.DATA_DIR = Path(tempfile.mkdtemp())

with ui.serving() as base, sync_playwright() as p:
    client = ui.user()
    session = client.cookies["session"]
    sheet_id = ui.sheet(client, *pages)["id"]
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 1400, "height": 1400})
    # The tour would lie over the sheet, and so would the zoom buttons in a lower window.
    context.add_init_script("localStorage.setItem('tour', '1')")
    # The session cookie is Secure and this server speaks http, so it goes by hand.
    context.add_cookies([{"name": "session", "value": session, "url": base}])
    page = context.new_page()
    page.goto(f"{base}/blatt/{sheet_id}")
    page.locator('main.editor[data-ready="1"]').wait_for()
    page.locator(".sheet").first.screenshot(path=screen)
    # Before the server stops: leaving the editor saves.
    browser.close()
    cookie = {"Cookie": f"session={session}"}
    res = httpx.get(f"{base}/api/sheets/{sheet_id}/pdf", headers=cookie, timeout=60)

# Page 1 of the PDF, as wide in pixels as the editor's sheet. A PNG holds its width after 16 bytes.
(width,) = struct.unpack(">I", screen.read_bytes()[16:20])
first = pypdfium2.PdfDocument(res.content)[0]
bitmap = first.render(scale=width / first.get_width(), rev_byteorder=True)
w, h, stride = bitmap.width, bitmap.height, bitmap.stride
rows = b"".join(b"\x00" + bytes(bitmap.buffer[y * stride : y * stride + w * 3]) for y in range(h))
head = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
parts = (b"IHDR", head), (b"IDAT", zlib.compress(rows)), (b"IEND", b"")
printed.write_bytes(b"\x89PNG\r\n\x1a\n" + b"".join(ui.chunk(k, d) for k, d in parts))
print(screen, printed, sep="\n")
