"""A page ground in the editor, and under the blocks in the PDF."""

import io

import httpx
import pypdfium2
from playwright.sync_api import expect
from test_grounds import jpeg, pdf_of
from ui import RECT, TEXT, box, doc, pick, png, user

PLACEHOLDER = "[Platzhalter] Text zu Rechten: noch offen."


def ground(page):
    return page.locator(".sheet .ground")


def open_pages(page):
    """Blattform starts with the page panel shut. Vorlagen opens it."""
    page.get_by_role("tab", name="Vorlagen").click()
    expect(page.get_by_role("heading", name="Hintergrund")).to_be_visible()


def give(page, name, mime, data):
    page.get_by_label("Hintergrunddatei").set_input_files(
        {"name": name, "mimeType": mime, "buffer": data}
    )


# The status line is not enough. An undo that puts back the saved sheet never leaves
# "Gespeichert", and a save that finishes before the next line is read has left it already.
SHEET = """async (want) => {
    const id = location.pathname.split("/").pop();
    const res = await fetch("/api/sheets/" + id, { cache: "no-store" });
    if (!res.ok) return false;
    const pages = (await res.json()).doc?.pages ?? [];
    if (want === "one") {
        const ground = pages[0] && pages[0].ground;
        const cut = (ground && ground.cut) || [];
        return pages.length === 1 && !!ground && cut.join(",") === "0,0,0,0"
            && (ground.opacity ?? 1) === 1 && (ground.turns ?? 0) === 0;
    }
    return pages.length === 2 && pages.every((p) => p.ground && p.ground.upload)
        && pages[0].ground.upload !== pages[1].ground.upload;
}"""


def test_a_photo_is_the_ground_under_the_blocks_and_undo_takes_it_back(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    open_pages(page)
    expect(page.locator("[data-placeholder=rights]")).to_have_text(PLACEHOLDER)
    hint = page.locator(".ground-box .hint").first
    expect(hint).to_contain_text("30 MB")
    expect(hint).to_contain_text("20 Seiten")
    give(page, "foto.png", "image/png", png())
    expect(ground(page)).to_have_count(1)
    expect(ground(page)).to_have_attribute("data-opacity", "1")
    expect(ground(page)).to_have_attribute("data-turns", "0")
    # The picture is not a block. A click on the page does not select it.
    expect(page.locator(".sheet .block[data-id]")).to_have_count(1)
    page.locator(".sheet").first.click(position={"x": 40, "y": 220})
    expect(page.locator(".block.sel")).to_have_count(0)
    on_top = page.locator(".block[data-id=a]").evaluate(
        """el => {
            const r = el.getBoundingClientRect();
            const hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
            return !!hit && (hit === el || el.contains(hit));
        }"""
    )
    assert on_top
    page.get_by_role("button", name="50 %", exact=True).click()
    expect(ground(page)).to_have_attribute("data-opacity", "0.5")
    page.get_by_label("Rückgängig", exact=True).click()
    expect(ground(page)).to_have_attribute("data-opacity", "1")
    page.get_by_label("Wiederholen", exact=True).click()
    expect(ground(page)).to_have_attribute("data-opacity", "0.5")
    page.get_by_label("Rückgängig", exact=True).click()
    page.get_by_role("button", name="Drehen", exact=True).click()
    expect(ground(page)).to_have_attribute("data-turns", "1")
    page.get_by_label("Rückgängig", exact=True).click()
    expect(ground(page)).to_have_attribute("data-turns", "0")
    page.get_by_role("button", name="Hintergrund bearbeiten", exact=True).click()
    expect(ground(page)).to_have_class("ground live")
    pick(page, "a")
    sheet = page.locator(".sheet.on").bounding_box()
    assert sheet
    before = ground(page).evaluate("el => el.getBoundingClientRect().left")
    x = sheet["x"] + sheet["width"] * 0.55
    y = sheet["y"] + sheet["height"] * 0.62
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 80, y + 36)
    page.mouse.up()
    moved = "(before) => { const el = document.querySelector('.sheet .ground'); return !!el && el.getBoundingClientRect().left !== before; }"
    page.wait_for_function(moved, arg=before, timeout=5000)
    page.get_by_label("Rückgängig", exact=True).click()
    back = "(before) => { const el = document.querySelector('.sheet .ground'); return !!el && el.getBoundingClientRect().left === before; }"
    page.wait_for_function(back, arg=before, timeout=5000)
    page.get_by_role("button", name="Zuschneiden", exact=True).click()
    expect(page.locator(".sheet .ground-handle")).to_have_count(4)
    page.get_by_role("button", name="Hintergrund entfernen", exact=True).click()
    expect(ground(page)).to_have_count(0)
    page.get_by_label("Rückgängig", exact=True).click()
    expect(ground(page)).to_have_count(1)
    page.wait_for_function(SHEET, arg="one", timeout=8000)
    stored = doc(page, client)["pages"][0]["ground"]
    assert stored["cut"] == [0, 0, 0, 0]
    assert stored["upload"] > 0
    assert stored.get("opacity", 1) == 1
    assert stored.get("turns", 0) == 0


def test_one_pdf_page_or_every_page_becomes_a_ground(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    open_pages(page)
    data = pdf_of((200, 200), (180, 180))
    give(page, "buch.pdf", "application/pdf", data)
    expect(page.get_by_text("Die PDF hat 2 Seiten.")).to_be_visible()
    page.get_by_label("Seite der PDF").fill("2")
    page.get_by_role("button", name="Diese Seite", exact=True).click()
    expect(ground(page)).to_have_count(1)
    expect(page.locator(".sheet")).to_have_count(1)
    page.get_by_role("button", name="Hintergrund entfernen", exact=True).click()
    expect(ground(page)).to_have_count(0)
    give(page, "buch.pdf", "application/pdf", data)
    expect(page.get_by_role("button", name="Alle Seiten", exact=True)).to_be_visible()
    page.get_by_role("button", name="Alle Seiten", exact=True).click()
    expect(ground(page)).to_have_count(2)
    page.wait_for_function(SHEET, arg="all", timeout=8000)
    pages = doc(page, client)["pages"]
    assert len(pages) == 2
    assert pages[0]["blocks"][0]["id"] == "a"
    assert pages[1]["blocks"] == []
    assert pages[0]["ground"]["upload"] != pages[1]["ground"]["upload"]


def test_the_pdf_prints_the_ground_under_a_white_block(server):
    client = user()
    made = client.post("/api/grounds", files={"file": ("foto.jpg", jpeg(), "image/jpeg")}).json()[
        "made"
    ][0]
    white = {**RECT, "fill": "#ffffff", "stroke": "none"}
    doc_ = {
        "pages": [
            {
                "blocks": [box("cover", "shape", white, x=0, y=0, w=40, h=40)],
                "ground": {
                    "upload": made["id"],
                    "ratio": made["width"] / made["height"],
                    "cut": [0, 0, 0, 0],
                },
            }
        ],
        "guides": {"x": [], "y": []},
        "grid": 0,
    }
    sheet = client.post("/api/sheets", json={"title": "Grund", "doc": doc_}).json()
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{sheet['id']}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200, res.text[:300]
    picture = pypdfium2.PdfDocument(io.BytesIO(res.content))[0].render(scale=2).to_pil()
    picture = picture.convert("RGB")
    per_mm = picture.height / 297

    def pixel(x_mm, y_mm):
        return picture.getpixel((int(x_mm * per_mm), int(y_mm * per_mm)))

    # The white shape covers the red ground. The middle of the page stays red.
    cover = pixel(20, 20)
    assert min(cover) > 240, cover
    red = pixel(105, 150)
    assert red[0] > 180 and red[1] < 40 and red[2] < 40, red
