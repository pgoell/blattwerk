"""A sheet as the editor shows it and as the PDF prints it, each as a PNG, and where they differ.

    mise run shot -- pages.json out/
    mise run shot -- tests/corpus/sheet-1.json out/ --page 2 --loesungen

pages.json holds the pages of the sheet, each a list of blocks, or a whole sheet as a corpus file
has it, {"title": ..., "doc": {...}}, whose doc is posted as it is. `--page N` shoots page N (from
0), `--loesungen` the answer key. Writes screen.png, pdf.png and
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

args = sys.argv[1:]
page = int(args[args.index("--page") + 1]) if "--page" in args else 0
solved = "--loesungen" in args
pages = json.loads(Path(args[0]).read_text())
# A corpus file holds the whole doc (#543), with what the sheet has beside its pages.
whole = pages.get("doc") if isinstance(pages, dict) else None
# A sheet with Lernwörter comes as {"pages": [...], "words": [...]}.
words = pages.get("words") if isinstance(pages, dict) else None
pages = pages["pages"] if isinstance(pages, dict) and not whole else pages
out = Path(args[1])
out.mkdir(parents=True, exist_ok=True)
# Before the first user: the database is made where this points.
db.DATA_DIR = Path(tempfile.mkdtemp())

with ui.serving() as base, sync_playwright() as p:
    client = ui.user()
    # The browser whose limits pixels.py holds.
    browser = getattr(p, ui.BROWSER).launch()
    if whole:
        made = client.post("/api/sheets", json={"title": pages.get("title", "Shot"), "doc": whole})
        sheet_id = made.json()["id"]
    else:
        sheet_id = ui.sheet(client, *pages, words=words)["id"]
    screen, printed = pixels.screen_and_print(
        browser, base, client, sheet_id, page=page, solved=solved
    )
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
