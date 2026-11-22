"""A sheet's pages as a Word file: a page to a page, with no margin of Word's.

Each page is one section with one empty line. The pictures and the text boxes are anchored to that
line and placed from the page's corner, in front of the text, as "Vor den Text" in Word.
"""

import io
from xml.sax.saxutils import escape, quoteattr

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.oxml import parse_xml
from docx.shared import Emu, Pt

from blattwerk.office_parts import Page, Picture, Text

EMU = 36000
NS = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
    'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"'
)
JC = {"left": "left", "center": "center", "right": "right"}
ANCHOR = {"top": "t", "middle": "ctr", "bottom": "b"}


def emu(mm: float) -> int:
    return round(mm * EMU)


def anchor(n: int, x: float, y: float, w: float, h: float, alt: str, inner: str, under=False):
    """A drawing at a place on the page, counted from the page's corner. `n` is its number in the
    file, and the higher lies over the lower."""
    return (
        f'<wp:anchor {NS} distT="0" distB="0" distL="0" distR="0" simplePos="0" '
        f'relativeHeight="{n}" behindDoc="{int(under)}" locked="0" layoutInCell="1" '
        'allowOverlap="1"><wp:simplePos x="0" y="0"/>'
        f'<wp:positionH relativeFrom="page"><wp:posOffset>{emu(x)}</wp:posOffset></wp:positionH>'
        f'<wp:positionV relativeFrom="page"><wp:posOffset>{emu(y)}</wp:posOffset></wp:positionV>'
        f'<wp:extent cx="{emu(w)}" cy="{emu(h)}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
        f'<wp:wrapNone/><wp:docPr id="{n}" name="Blattomat {n}" descr={quoteattr(alt)}/>'
        f"<wp:cNvGraphicFramePr/>{inner}</wp:anchor>"
    )


def run_xml(box: Text, piece) -> str:
    look = f'<w:rFonts w:ascii="{box.font}" w:hAnsi="{box.font}" w:cs="{box.font}"/>'
    if piece:
        look += f'<w:b w:val="{int(piece.bold)}"/><w:i w:val="{int(piece.italic)}"/>'
        look += f'<w:color w:val="{piece.color}"/>'
    if box.tracking:
        # Twentieths of a point between the letters.
        look += f'<w:spacing w:val="{round(box.tracking * 20)}"/>'
    # Half points.
    look += f'<w:sz w:val="{round(box.size * 2)}"/><w:szCs w:val="{round(box.size * 2)}"/>'
    if piece and piece.underline:
        look += '<w:u w:val="single"/>'
    lines = piece.text.split("\n") if piece else [""]
    words = "<w:br/>".join(f'<w:t xml:space="preserve">{escape(line)}</w:t>' for line in lines)
    return f"<w:r><w:rPr>{look}</w:rPr>{words}</w:r>"


def text_xml(n: int, box: Text) -> str:
    paras = "".join(
        # A fixed distance from line to line, in twentieths of a point, as the sheet's line height.
        f'<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="{round(box.line * 20)}" '
        f'w:lineRule="exact"/><w:jc w:val="{JC[box.align]}"/></w:pPr>'
        + "".join(run_xml(box, piece) for piece in para or [None])
        + "</w:p>"
        for para in box.paras
    )
    fill = (
        f'<a:solidFill><a:srgbClr val="{box.fill}"/></a:solidFill>' if box.fill else "<a:noFill/>"
    )
    line = (
        f'<a:ln w="{emu(box.stroke_w)}"><a:solidFill><a:srgbClr val="{box.stroke}"/></a:solidFill>'
        "</a:ln>"
        if box.stroke
        else "<a:ln><a:noFill/></a:ln>"
    )
    down, across = emu(box.inset[0]), emu(box.inset[1])
    # A text that stands at the top lets its box grow down with it: Word cuts what runs over.
    fit = "<a:spAutoFit/>" if box.valign == "top" else "<a:noAutofit/>"
    shape = (
        '<a:graphic><a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">'
        '<wps:wsp><wps:cNvSpPr txBox="1"/><wps:spPr>'
        f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{emu(box.w)}" cy="{emu(box.h)}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{fill}{line}</wps:spPr>'
        f"<wps:txbx><w:txbxContent>{paras}</w:txbxContent></wps:txbx>"
        f'<wps:bodyPr rot="0" vert="horz" wrap="square" lIns="{across}" tIns="{down}" '
        f'rIns="{across}" bIns="{down}" anchor="{ANCHOR[box.valign]}">{fit}</wps:bodyPr>'
        "</wps:wsp></a:graphicData></a:graphic>"
    )
    words = " ".join(piece.text for para in box.paras for piece in para)
    # A shape of Word 2010 and later: a reader that knows none skips it.
    return (
        f'<w:r {NS}><mc:AlternateContent><mc:Choice Requires="wps"><w:drawing>'
        f"{anchor(n, box.x, box.y, box.w, box.h, words, shape)}"
        "</w:drawing></mc:Choice></mc:AlternateContent></w:r>"
    )


def write(pages: list[Page], title: str) -> bytes:
    file = Document()
    file.core_properties.title = title
    file.core_properties.author = "Blattomat"
    n = 0
    for i, page in enumerate(pages):
        section = file.sections[0] if i == 0 else file.add_section(WD_SECTION.NEW_PAGE)
        section.orientation = WD_ORIENT.LANDSCAPE if page.w > page.h else WD_ORIENT.PORTRAIT
        section.page_width, section.page_height = Emu(emu(page.w)), Emu(emu(page.h))
        section.left_margin = section.right_margin = Emu(0)
        section.top_margin = section.bottom_margin = Emu(0)
        section.header_distance = section.footer_distance = Emu(0)
        # The page's one line: all that lies on the page hangs on it.
        line = file.add_paragraph()
        line.paragraph_format.space_before = line.paragraph_format.space_after = Pt(0)
        for item in page.items:
            n += 1
            if isinstance(item, Picture):
                run = line.add_run()
                # Word's own picture in the line, taken out of it and placed on the page.
                size = Emu(emu(item.w)), Emu(emu(item.h))
                graphic = file.part.new_pic_inline(io.BytesIO(item.data), *size).graphic
                placed = parse_xml(
                    anchor(n, item.x, item.y, item.w, item.h, item.alt, "", item.under)
                )
                placed.append(graphic)
                drawing = parse_xml(f"<w:drawing {NS}/>")
                drawing.append(placed)
                run._r.append(drawing)
            else:
                line._p.append(parse_xml(text_xml(n, item)))
    out = io.BytesIO()
    file.save(out)
    return out.getvalue()
