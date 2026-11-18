"""PowerPoint and Word: a sheet as a file a teacher goes on working with.

Chromium draws the sheet's print page, as for the PDF. A plain text becomes a text box of the
file's own, which can be typed in. Every other block is a picture of itself at its place, which
can be moved, sized and deleted. The file does not carry the fonts: a text box looks as on the
sheet where the font is installed, and takes another font where it is not.
"""

import io
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request, Response
from PIL import Image
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from blattwerk import office_docx, office_pptx
from blattwerk.auth import Teacher
from blattwerk.db import Con, Id
from blattwerk.office_parts import Page, Picture, Run, Text
from blattwerk.pdf import PRINT_WAIT, drawn, new_token
from blattwerk.schema import mended
from blattwerk.sheets import find

router = APIRouter(prefix="/api")

# Device pixels to a CSS pixel in a block's picture: 288 to the inch, enough for a line in print.
SCALE = 3
# CSS pixels to a mm, as the page draws (K in frontend/src/sheet/box.ts).
K = 96 / 25.4
# A picture with no see-through part and more bytes than this is a photo: it goes in as a JPEG.
PHOTO = 400_000

# The fonts a text box may name: the print scripts. A joined script in another font is another
# script, so a text in one stays a picture.
FONTS = {"andika": "Andika", "nord": "Fibel Nord", "sued": "Fibel Sued"}
# The props a text box of the file can show. A text with any other prop set stays a picture.
SHOWN = {
    "text",
    "rich",
    "size",
    "align",
    "font",
    "bold",
    "italic",
    "underline",
    "color",
    "spacing",
    "tracking",
    "valign",
    "kind",
    "fill",
    "stroke",
    "strokeWidth",
    "opacity",
    "strokeOpacity",
    "fit",
    "floor",
    "breaks",
}
OFF = (None, False, 0, "", "none")
LOOKS = {"text", "bold", "italic", "underline", "color"}

# Hides all of the page but the parts named with data-on, on no ground: what is not drawn is
# see-through in the picture. Of a part named with data-mark, only its numbering shows.
ALONE = """
html, body, #root, .print, .print .paper { background: transparent !important; }
.print .scaled > :not([data-on]) { display: none !important; }
.print .scaled > [data-mark] > :not(.mark) { visibility: hidden !important; }
"""
# The parts of page `n`, in the order they lie: each one's block id, if it is a block, its class
# and its z. And the page's place.
PARTS = """(n) => {
  const paper = document.querySelectorAll(".print .paper")[n];
  const box = paper.getBoundingClientRect();
  return {
    x: box.x + scrollX, y: box.y + scrollY, w: box.width, h: box.height,
    parts: [...paper.querySelector(".scaled").children].map((el) => ({
      id: el.dataset.block ?? null,
      block: el.classList.contains("block"),
      over: el.classList.contains("key") || el.classList.contains("variant"),
      z: Number(getComputedStyle(el).zIndex) || 0,
    })),
  };
}"""
# Shows the parts `on` of page `n` alone, and gives the box that holds all they draw, on the page.
SHOW = """([n, on, mark]) => {
  const paper = document.querySelectorAll(".print .paper")[n];
  document.querySelectorAll("[data-on]").forEach((el) => {
    el.removeAttribute("data-on");
    el.removeAttribute("data-mark");
  });
  const page = paper.getBoundingClientRect();
  let [l, t, r, b] = [Infinity, Infinity, -Infinity, -Infinity];
  const parts = paper.querySelector(".scaled").children;
  for (const i of on) {
    const el = parts[i];
    el.setAttribute("data-on", "");
    if (mark) el.setAttribute("data-mark", "");
    const drawn = mark ? el.querySelectorAll(".mark, .mark *") : [el, ...el.querySelectorAll("*")];
    for (const inner of drawn) {
      const box = inner.getBoundingClientRect();
      if (!box.width && !box.height) continue;
      [l, t] = [Math.min(l, box.left), Math.min(t, box.top)];
      [r, b] = [Math.max(r, box.right), Math.max(b, box.bottom)];
    }
  }
  [l, t] = [Math.max(Math.floor(l) - 1, page.left), Math.max(Math.floor(t) - 1, page.top)];
  [r, b] = [Math.min(Math.ceil(r) + 1, page.right), Math.min(Math.ceil(b) + 1, page.bottom)];
  return r > l && b > t ? { x: l + scrollX, y: t + scrollY, width: r - l, height: b - t } : null;
}"""


def rgb(colour: object, default: str | None = None) -> str | None:
    """A colour as the files write it, rrggbb. Anything that is no #rrggbb is the default."""
    if isinstance(colour, str) and len(colour) == 7 and colour[0] == "#":
        try:
            int(colour[1:], 16)
            return colour[1:].upper()
        except ValueError:
            pass
    return default


def plain(block: dict) -> bool:
    """Whether a block is a text the file can hold as a text box of its own: upright, in a print
    script, in a plain box, with no look the file's text has no like for."""
    props = block.get("props")
    if block.get("type") != "text" or not isinstance(props, dict) or block.get("angle"):
        return False
    if any(props[key] not in OFF for key in props if key not in SHOWN):
        return False
    if props.get("kind", "rect") != "rect" or props.get("font", "andika") not in FONTS:
        return False
    if props.get("opacity", 1) != 1 or props.get("strokeOpacity", 1) != 1:
        return False
    if not isinstance(props.get("size"), int | float) or not isinstance(props.get("text"), str):
        return False
    # A formula inside the text is drawn, not written.
    if "\\f{" in props["text"]:
        return False
    for para in props.get("rich") or []:
        if para.get("list") or para.get("level"):
            return False
        for run in para.get("runs", []):
            if any(run[key] not in OFF for key in run if key not in LOOKS):
                return False
            if "\\f{" in run.get("text", ""):
                return False
    return True


def text_of(block: dict) -> Text | None:
    """The text box of a plain text, or nothing for one that would show nothing."""
    props = block["props"]
    colour = rgb(props.get("color"), "222222") or "222222"

    def run(piece: dict) -> Run:
        return Run(
            piece.get("text", ""),
            bool(piece.get("bold", props.get("bold"))),
            bool(piece.get("italic", props.get("italic"))),
            bool(piece.get("underline") or props.get("underline")),
            rgb(piece.get("color"), colour) or colour,
        )

    if props.get("rich"):
        paras = [[run(piece) for piece in para.get("runs", [])] for para in props["rich"]]
    else:
        paras = [[run({"text": line})] for line in props["text"].split("\n")]
    fill, stroke = rgb(props.get("fill")), rgb(props.get("stroke"))
    if not fill and not stroke and not any(r.text.strip() for para in paras for r in para):
        return None
    # As `inset` in frontend/src/sheet/look.ts: a box with a fill or a border keeps its text off it.
    edge = props.get("strokeWidth", 0.5) if stroke else 0
    spacing = props.get("spacing", 1.3)
    return Text(
        block["x"],
        block["y"],
        block["w"],
        block["h"],
        paras,
        FONTS[props.get("font", "andika")],
        props["size"],
        props["size"] * (spacing if isinstance(spacing, int | float) else 1.3),
        props["size"] * (props.get("tracking") or 0),
        props.get("align") if props.get("align") in ("center", "right") else "left",
        props.get("valign") if props.get("valign") in ("middle", "bottom") else "top",
        fill,
        stroke,
        edge,
        (1.3 + edge, 2.5 + edge) if fill or stroke else (0, 0),
    )


def cut(shot: bytes, clip: dict, page: dict, alt: str, under: bool = False) -> Picture | None:
    """The picture of a shot of the page, cut to what it draws. Nothing where it draws nothing."""
    image = Image.open(io.BytesIO(shot)).convert("RGBA")
    box = image.getchannel("A").getbbox()
    if not box:
        return None
    image = image.crop(box)
    out = io.BytesIO()
    image.save(out, "PNG")
    ext: Literal["png", "jpg"] = "png"
    solid = image.getchannel("A").getextrema()[0] == 255
    # The page's own picture lies on the white paper, so its see-through parts are white.
    if (solid or under) and out.tell() > PHOTO:
        white = Image.new("RGB", image.size, "white")
        white.paste(image, mask=image.getchannel("A"))
        out, ext = io.BytesIO(), "jpg"
        white.save(out, "JPEG", quality=88, dpi=(96 * SCALE, 96 * SCALE))
    return Picture(
        (clip["x"] - page["x"] + box[0] / SCALE) / K,
        (clip["y"] - page["y"] + box[1] / SCALE) / K,
        (box[2] - box[0]) / SCALE / K,
        (box[3] - box[1]) / SCALE / K,
        out.getvalue(),
        ext,
        alt,
        under,
    )


def alt_of(block: dict) -> str:
    """What a block's picture says to a screen reader: its words, or else what it is."""
    props = block.get("props")
    words = props.get("text") if isinstance(props, dict) else None
    return words if isinstance(words, str) and words.strip() else str(block.get("type", ""))


def pages_of(tab, doc: dict) -> list[Page]:
    """The pages of the print page that `tab` has drawn, as pictures and text boxes."""
    tab.add_style_tag(content=ALONE)
    out = []
    for n, stored in enumerate(doc["pages"]):
        blocks = {b.get("id"): b for b in stored.get("blocks", []) if isinstance(b, dict)}
        page = tab.evaluate(PARTS, n)
        # A4, upright or on its side.
        landscape = stored.get("landscape", doc.get("landscape"))
        made = Page(*((297, 210) if landscape else (210, 297)))

        def shoot(on: list[int], alt: str, mark=False, under=False, page=page, n=n):
            clip = tab.evaluate(SHOW, [n, on, mark])
            if not clip:
                return None
            shot = tab.screenshot(clip=clip, full_page=True, omit_background=True)
            return cut(shot, clip, page, alt, under)

        parts = list(enumerate(page["parts"]))
        ground = [i for i, part in parts if not part["block"] and not part["over"]]
        # The page's picture and its number lie under the blocks, the answer key's mark over them.
        made.items.append(shoot(ground, "Hintergrund", under=True))
        for i, part in sorted((p for p in parts if p[1]["block"]), key=lambda p: p[1]["z"]):
            block = blocks.get(part["id"], {})
            box = text_of(block) if plain(block) else None
            if box:
                made.items.append(box)
                if block.get("mark"):
                    made.items.append(shoot([i], str(block["mark"]), mark=True))
            elif not plain(block):
                made.items.append(shoot([i], alt_of(block)))
        made.items.append(shoot([i for i, part in parts if part["over"]], "Lösungen"))
        made.items = [item for item in made.items if item]
        out.append(made)
    return out


def drawn_pages(request: Request, sheet: dict, solved: bool) -> list[Page]:
    # Chromium calls this same server, on the port the request came in by.
    url = f"http://127.0.0.1:{request.scope['server'][1]}/druck/{sheet['id']}"
    doc = mended(sheet["doc"])
    # A sheet from before pages holds its blocks at the top: one page.
    doc = doc if "pages" in doc else {**doc, "pages": [{"blocks": doc.get("blocks", [])}]}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(
                viewport={"width": 1400, "height": 1400},
                device_scale_factor=SCALE,
                extra_http_headers={"X-Render-Token": new_token(sheet["id"])},
            )
            tab = context.new_page()
            errors: list[str] = []
            tab.on("pageerror", lambda error: errors.append(error.message))
            # The page as it prints, which is how the PDF has it.
            tab.emulate_media(media="print")
            tab.goto(url + ("?loesungen" if solved else ""))
            try:
                drawn(tab, errors, PRINT_WAIT)
            except PlaywrightTimeout:
                raise HTTPException(504) from None
            return pages_of(tab, doc)
        finally:
            browser.close()


def export(kind: str, request: Request, sheet: dict, solved: bool) -> Response:
    write, media = KINDS[kind]
    data = write(drawn_pages(request, sheet, solved), sheet["title"])
    name = quote(sheet["title"] + (" Lösungen" if solved else "") + "." + kind)
    return Response(
        data,
        media_type=media,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{name}"},
    )


KINDS = {
    "pptx": (
        office_pptx.write,
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ),
    "docx": (
        office_docx.write,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
}


@router.get("/sheets/{sheet_id}/pptx")
def pptx(sheet_id: Id, request: Request, user: Teacher, con: Con, solved: bool = False) -> Response:
    return export("pptx", request, find(con, sheet_id, user), solved)


@router.get("/sheets/{sheet_id}/docx")
def docx(sheet_id: Id, request: Request, user: Teacher, con: Con, solved: bool = False) -> Response:
    return export("docx", request, find(con, sheet_id, user), solved)
