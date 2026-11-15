import io
import zipfile

import httpx
import pytest
from docx import Document
from docx.shared import Mm
from fastapi.testclient import TestClient
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from ui import ITEM, RULING, TEXT, block, maths, sheet, user

from blattwerk import office
from blattwerk.app import app

BOXED = {**TEXT, "fill": "#ffee88", "stroke": "#222222", "strokeWidth": 1}


def text(props, **more):
    return {**block("text", 20, 20, props), **more}


def test_a_stranger_gets_no_file():
    client = user()
    stranger = user()
    mine = sheet(client, [])
    for kind in ("pptx", "docx"):
        assert stranger.get(f"/api/sheets/{mine['id']}/{kind}").status_code == 404
        assert client.get(f"/api/sheets/99/{kind}").status_code == 404
        assert TestClient(app).get(f"/api/sheets/{mine['id']}/{kind}").status_code == 401


@pytest.mark.parametrize(
    "props",
    [
        TEXT,
        BOXED,
        {**TEXT, "font": "nord", "bold": True, "valign": "middle", "tracking": 0.1},
        {**TEXT, "rich": [{"runs": [{"text": "Hal", "bold": True}, {"text": "lo"}]}]},
        # Off is as good as absent.
        {**TEXT, "syllables": False, "gapWidth": 0, "kind": "rect"},
    ],
)
def test_a_plain_text_is_a_text_box(props):
    assert office.plain(text(props))
    assert office.text_of(text(props))


@pytest.mark.parametrize(
    "props",
    [
        # A joined script in another font is another script.
        {**TEXT, "font": "va"},
        {**TEXT, "syllables": True},
        {**TEXT, "trace": "dotted"},
        {**TEXT, "kind": "bubble"},
        {**TEXT, "fill": "#ffee88", "opacity": 0.5},
        {**TEXT, "text": "Rechne \\f{3/4}"},
        {**TEXT, "lines": 5},
        {**TEXT, "rich": [{"runs": [{"text": "Hallo", "gap": True}]}]},
        ITEM,
    ],
)
def test_a_text_with_a_look_of_the_sheet_stays_a_picture(props):
    assert not office.plain(text(props))


def test_a_turned_text_and_another_block_stay_pictures():
    assert not office.plain(text(TEXT, angle=30))
    assert not office.plain(block("ruling", 20, 20, RULING))


def test_a_text_box_takes_the_text_s_look():
    rich = [
        {"runs": [{"text": "Lies ", "color": "#e02424"}, {"text": "genau", "italic": True}]},
        {"runs": []},
        {"runs": [{"text": "und schreibe", "bold": False, "underline": True}]},
    ]
    props = {**BOXED, "bold": True, "size": 20, "spacing": 1.5, "align": "center", "rich": rich}
    box = office.text_of(text(props))
    assert box
    assert (box.x, box.y, box.w, box.h) == (15, 20, 180, 20)
    assert (box.font, box.size, box.line, box.align, box.valign) == (
        "Andika",
        20,
        30,
        "center",
        "top",
    )
    assert (box.fill, box.stroke, box.stroke_w) == ("FFEE88", "222222", 1)
    # As the sheet: 1.3 mm down and 2.5 mm across, and the border.
    assert box.inset == (2.3, 3.5)
    first, empty, last = box.paras
    assert [(r.text, r.bold, r.italic, r.color) for r in first] == [
        ("Lies ", True, False, "E02424"),
        ("genau", True, True, "222222"),
    ]
    assert empty == []
    assert (last[0].bold, last[0].underline) == (False, True)


def test_a_text_of_no_words_and_no_box_is_left_out():
    assert office.text_of(text({**TEXT, "text": " \n"})) is None
    assert office.text_of(text({**BOXED, "text": ""}))


def fetch(server, client, mine, kind, **params):
    # The session cookie is Secure and this server speaks http, so it goes by hand.
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    url = f"{server}/api/sheets/{mine['id']}/{kind}"
    res = httpx.get(url, params=params, headers=cookie, timeout=60)
    assert res.status_code == 200
    return res


def a_sheet(client):
    return sheet(
        client,
        [
            {**block("text", 20, 12, {**TEXT, "text": "Rechne aus"}), "id": "t", "mark": "1."},
            {**block("maths", 40, 12, maths(client)), "z": 2},
            {
                **block("text", 60, 12, {**TEXT, "text": "Schreibe", "font": "va"}),
                "id": "v",
                "z": 3,
            },
        ],
        {"blocks": [block("name", 15, 10, {})], "landscape": True},
    )


@pytest.mark.timeout(120)
def test_powerpoint_holds_a_slide_to_a_page(server):
    client = user()
    mine = a_sheet(client)
    res = fetch(server, client, mine, "pptx")
    assert res.headers["content-type"].endswith("presentationml.presentation")
    assert res.headers["content-disposition"] == "attachment; filename*=UTF-8''Plus%20bis%2020.pptx"
    deck = Presentation(io.BytesIO(res.content))
    assert (deck.core_properties.title, deck.core_properties.author) == ("Plus bis 20", "Blattomat")
    # The slides are the first page's size, A4 upright.
    assert (deck.slide_width, deck.slide_height) == (Mm(210), Mm(297))
    first, second = deck.slides
    boxes = [s for s in first.shapes if s.shape_type == MSO_SHAPE_TYPE.TEXT_BOX]
    pictures = [s for s in first.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
    # The plain text is a text box at its place, in its font and size.
    assert [b.text_frame.text for b in boxes] == ["Rechne aus"]
    assert (boxes[0].left, boxes[0].top, boxes[0].width) == (Mm(15), Mm(20), Mm(180))
    run = boxes[0].text_frame.paragraphs[0].runs[0]
    assert (run.font.name, run.font.size.pt) == ("Andika", 14)
    # Its numbering, the sums and the text in a joined script are a picture each.
    assert len(pictures) == 3
    mark, sums, joined = pictures
    assert mark.left + mark.width <= Mm(15) and abs(mark.top - Mm(20)) < Mm(3)
    # A picture is cut to what it draws, inside its block's box.
    assert Mm(15) <= sums.left and sums.left + sums.width <= Mm(195)
    assert Mm(40) <= sums.top and sums.top + sums.height <= Mm(52)
    assert Mm(60) <= joined.top + joined.height / 2 <= Mm(72)
    # The page on its side lies whole on its upright slide.
    (name,) = second.shapes
    assert name.shape_type == MSO_SHAPE_TYPE.PICTURE
    assert name.left + name.width <= Mm(210)


@pytest.mark.timeout(120)
def test_word_holds_a_page_to_a_page_and_the_answer_key(server):
    client = user()
    mine = a_sheet(client)
    res = fetch(server, client, mine, "docx", solved=True)
    assert res.headers["content-type"].endswith("wordprocessingml.document")
    name = "Plus%20bis%2020%20L%C3%B6sungen.docx"
    assert res.headers["content-disposition"] == f"attachment; filename*=UTF-8''{name}"
    file = Document(io.BytesIO(res.content))
    assert (file.core_properties.title, file.core_properties.author) == ("Plus bis 20", "Blattomat")
    # A section to a page, each the size of its paper with no margin.
    # Word counts a page in twentieths of a point.
    sizes = [
        (round((s.page_width or Mm(0)).mm), round((s.page_height or Mm(0)).mm))
        for s in file.sections
    ]
    assert sizes == [(210, 297), (297, 210)]
    assert all(s.left_margin == 0 and s.top_margin == 0 for s in file.sections)
    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
        body = z.read("word/document.xml").decode()
        media = [n for n in z.namelist() if n.startswith("word/media/")]
    assert body.count("<wps:txbx>") == 1
    assert ">Rechne aus</w:t>" in body
    assert f"<wp:posOffset>{Mm(15)}</wp:posOffset>" in body
    # The numbering, the sums, the joined text, the name line, and on each page the key's mark.
    assert body.count("<pic:pic") == 6
    assert len(media) >= 5
    plain = fetch(server, client, mine, "docx")
    with zipfile.ZipFile(io.BytesIO(plain.content)) as z:
        assert z.read("word/document.xml").decode().count("<pic:pic") == 4
