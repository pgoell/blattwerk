"""A sheet's pages as a PowerPoint file: a slide to a page, the size of the paper."""

import io

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.util import Emu, Pt

from blattwerk.office_parts import Page, Picture, Text

# English Metric Units to a mm: the unit both files measure in.
EMU = 36000
ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}
ANCHOR = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE, "bottom": MSO_ANCHOR.BOTTOM}


def text_box(slide, box: Text, at, f: float) -> None:
    shape = slide.shapes.add_textbox(*at(box.x, box.y), Emu(round(box.w * f * EMU)), Emu(1))
    shape.height = Emu(round(box.h * f * EMU))
    frame = shape.text_frame
    frame.word_wrap = True
    # The box keeps its size, as on the sheet, and the text may run over its foot.
    frame.auto_size = MSO_AUTO_SIZE.NONE
    frame.vertical_anchor = ANCHOR[box.valign]
    frame.margin_top = frame.margin_bottom = Emu(round(box.inset[0] * f * EMU))
    frame.margin_left = frame.margin_right = Emu(round(box.inset[1] * f * EMU))
    if box.fill:
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(box.fill)
    if box.stroke:
        shape.line.color.rgb = RGBColor.from_string(box.stroke)
        shape.line.width = Emu(round(box.stroke_w * f * EMU))
    for n, para in enumerate(box.paras):
        p = frame.paragraphs[0] if n == 0 else frame.add_paragraph()
        p.alignment = ALIGN[box.align]
        # A length is a fixed distance from line to line, as the sheet's line height is.
        p.line_spacing = Pt(box.line * f)
        p.space_before = p.space_after = Pt(0)
        # A paragraph with no words still is a line of the text's size.
        for piece in para or [None]:
            lines = piece.text.split("\n") if piece else [""]
            for i, line in enumerate(lines):
                if i:
                    p.add_line_break()
                run = p.add_run()
                run.text = line
                font = run.font
                font.name = box.font
                font.size = Pt(box.size * f)
                if piece:
                    font.bold, font.italic, font.underline = (
                        piece.bold,
                        piece.italic,
                        piece.underline,
                    )
                    font.color.rgb = RGBColor.from_string(piece.color)
                if box.tracking:
                    # Hundredths of a point between the letters.
                    run._r.get_or_add_rPr().set("spc", str(round(box.tracking * f * 100)))


def write(pages: list[Page], title: str) -> bytes:
    deck = Presentation()
    deck.core_properties.title = title
    deck.core_properties.author = "Blattomat"
    # A file has one size for all its slides: the first page's. A page that lies the other way is
    # drawn smaller, whole and in the middle of its slide.
    wide, high = (pages[0].w, pages[0].h) if pages else (210, 297)
    deck.slide_width, deck.slide_height = Emu(round(wide * EMU)), Emu(round(high * EMU))
    blank = deck.slide_layouts[6]
    for page in pages:
        slide = deck.slides.add_slide(blank)
        f = min(wide / page.w, high / page.h)
        dx, dy = (wide - page.w * f) / 2, (high - page.h * f) / 2

        def at(x: float, y: float, f=f, dx=dx, dy=dy):
            return Emu(round((x * f + dx) * EMU)), Emu(round((y * f + dy) * EMU))

        for item in page.items:
            if isinstance(item, Picture):
                shape = slide.shapes.add_picture(
                    io.BytesIO(item.data),
                    *at(item.x, item.y),
                    Emu(round(item.w * f * EMU)),
                    Emu(round(item.h * f * EMU)),
                )
                shape._element.nvPicPr.cNvPr.set("descr", item.alt)
            else:
                text_box(slide, item, at, f)
    out = io.BytesIO()
    deck.save(out)
    return out.getvalue()
