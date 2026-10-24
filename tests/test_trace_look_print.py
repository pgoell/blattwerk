"""The screen and the PDF of a sheet that uses every trace look agree, and the PDF holds no picture."""

import re

import httpx
from pixels import over, screen_and_print
from test_trace_look import INK, place
from ui import RECT, RULING, TABLE, TEXT, sheet, user


def look_sheet():
    """One sheet with every look and both fadings: a text, a shape with a fill, a table, two
    Lineaturen and a Karo."""
    return [
        place(
            "t1",
            "text",
            {**TEXT, "text": "Hallo " * 20, "trace": True, "fade": "row"},
            x=15,
            y=20,
            w=180,
            h=25,
        ),
        place(
            "t2",
            "text",
            {**TEXT, "text": "Hallo " * 20, "trace": "outline", "fade": "rows"},
            x=15,
            y=50,
            w=180,
            h=25,
        ),
        place(
            "t3",
            "text",
            {**TEXT, "text": "Hallo " * 20, "trace": "dotted", "font": "urff"},
            x=15,
            y=80,
            w=180,
            h=25,
        ),
        place(
            "s1",
            "shape",
            {**RECT, "fill": "#ffd43b", "text": "Hallo", "trace": "outline", "fade": "row"},
            x=15,
            y=110,
            w=180,
            h=25,
        ),
        place("tb", "table", {**TABLE, "trace": True, "fade": "rows"}, x=15, y=140, w=120, h=40),
        place(
            "r1",
            "ruling",
            {
                **RULING,
                "kind": "l1",
                "font": "va",
                "text": "Hallo Hallo\nHallo",
                "trace": "outline",
                "fade": "rows",
            },
            x=15,
            y=190,
            w=90,
            h=40,
        ),
        place(
            "r2",
            "ruling",
            {**RULING, "kind": "l1", "font": "urff", "text": "Hallo", "trace": "dotted"},
            x=15,
            y=235,
            w=90,
            h=40,
        ),
        place(
            "k",
            "ruling",
            {"kind": "k5", "color": INK, "text": "Hallo", "trace": "outline"},
            x=110,
            y=190,
            w=85,
            h=40,
        ),
    ]


def test_screen_and_pdf_agree(browser, server):
    """B9: the screen and the PDF of a sheet with every look and fading agree."""
    client = user()
    mine = sheet(client, look_sheet())
    screen, printed = screen_and_print(browser, server, client, mine["id"])
    assert not over(screen, printed)


def test_the_pdf_holds_no_picture(server):
    """B9: the PDF of that sheet has no image: letters, dots and outlines are vectors."""
    client = user()
    mine = sheet(client, look_sheet())
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{mine['id']}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    assert re.search(rb"/Subtype\s*/Image", res.content) is None
    # The looks did reach the print: the dotted text brought its cut along.
    assert b"Grundschrift-Punkt" in res.content
