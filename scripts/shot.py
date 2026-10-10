"""A sheet as the editor shows it and as the PDF prints it, each as a PNG, and where they differ.

    mise run shot -- pages.json out/

pages.json holds the pages of the sheet, each a list of blocks. Writes screen.png, pdf.png and
diff.png, the screen in pale with the pixels that differ in red, and prints each measure of
tests/pixels.py against its limit. BLATTWERK_BROWSER names the browser, as in the tests.
"""

import json
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from blattwerk import db

sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))
import pixels  # ty: ignore[unresolved-import]
import ui  # ty: ignore[unresolved-import]

pages = json.loads(Path(sys.argv[1]).read_text())
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
# Before the first user: the database is made where this points.
db.DATA_DIR = Path(tempfile.mkdtemp())

with ui.serving() as base, sync_playwright() as p:
    client = ui.user()
    # The browser whose limits pixels.py holds.
    browser = getattr(p, ui.BROWSER).launch()
    sheet_id = ui.sheet(client, *pages)["id"]
    screen, printed = pixels.screen_and_print(browser, base, client, sheet_id)
    browser.close()

found, marked = pixels.measures(screen, printed)
for name, data in ("screen.png", screen), ("pdf.png", printed), ("diff.png", marked):
    (out / name).write_bytes(data)
    print(out / name)
print(f"In {ui.BROWSER}:")
for name, (value, where) in found.items():
    limit = pixels.LIMITS[name]
    verdict = "over" if value >= limit else "within"
    if name == "page":
        print(f"{value * 100:.3f} % of the pixels differ, {verdict} the limit of {limit * 100} %")
    else:
        print(f"{name} {value:.3f}, {verdict} the limit of {limit}{where}")
