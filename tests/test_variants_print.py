# Tests of one behaviour each live in the sibling modules. Shared helpers stay here so existing imports keep working.

import io

import pypdf
import pypdfium2
from fastapi.testclient import TestClient
from ui import block, maths, sheet

from blattwerk.app import app


def chromium(token):
    return TestClient(app, base_url="https://testserver", headers={"X-Render-Token": token})


def fixture(client):
    """A sheet with room: maths, Suchsel, Schüttelwörter, Lösungswörter and a plain text."""
    return sheet(
        client,
        [
            block("maths", 20, 60, maths(client, count=12, max=100)),
            block(
                "suchsel",
                90,
                80,
                {
                    "words": ["Hund", "Katze", "Maus", "Igel"],
                    "cols": 10,
                    "rows": 10,
                    "ways": "down",
                    "caps": True,
                    "umlauts": True,
                    "show": "words",
                    "seed": 5,
                },
            ),
            {
                **block(
                    "text",
                    180,
                    30,
                    {
                        "text": "Der Hund bellt laut im Garten",
                        "size": 14,
                        "align": "left",
                        "mix": 7,
                    },
                ),
                "id": "mix",
            },
            {
                **block(
                    "text",
                    215,
                    40,
                    {
                        "text": "Der Hund bellt laut im Garten",
                        "size": 14,
                        "align": "left",
                        "bank": 3,
                        "rich": [
                            {
                                "runs": [
                                    {"text": "Der "},
                                    {"text": "Hund", "gap": True},
                                    {"text": " bellt "},
                                    {"text": "laut", "gap": True},
                                    {"text": " im "},
                                    {"text": "Garten", "gap": True},
                                ]
                            }
                        ],
                    },
                ),
                "id": "bank",
            },
            {
                **block("text", 260, 10, {"text": "Name:", "size": 14, "align": "left"}),
                "id": "name",
            },
        ],
    )


def cookie(client):
    return {"Cookie": f"session={client.cookies['session']}"}


def texts(data: bytes) -> list[str]:
    return [page.extract_text() for page in pypdf.PdfReader(io.BytesIO(data)).pages]


def letters(page: str) -> list[str]:
    """The letter lines of a page: the variant's mark."""
    return [line.strip() for line in page.splitlines() if line.strip() in ("A", "B", "C", "D")]


def rows_cols(exercises: list[dict]) -> tuple[int, int]:
    """The most rows and columns of the written grids of some exercises."""
    grids = [e["grid"] for e in exercises if "grid" in e]
    return max((g["rows"] for g in grids), default=0), max((g["cols"] for g in grids), default=0)


def written_props(client, **more):
    return maths(client, ops=["*"], max=10000, format="written", count=6, rest=True, **more)


LUECKEN = ["Schiffahrt", "Katzenhaus", "Vogelnest", "Pferdestall", "Schulhof", "Blumenbeet"]


def word_lines(page: str) -> list[str]:
    """The lines of a page that hold words: not blank, not the variant's letter or the key mark."""
    lines = [line.strip() for line in page.splitlines()]
    return [
        line.replace(" ", "")
        for line in lines
        if line and line not in ("A", "B", "C", "D") and not line.startswith("Lösungen")
    ]


def grid(page: str) -> list[str]:
    """The rows of a Suchsel grid on a page: lines of ten capitals, spaces between them or not."""
    rows = [line.replace(" ", "") for line in page.splitlines()]
    return [row for row in rows if len(row) == 10 and row.isupper()]


SENTENCE = "Der Hund bellt laut im Garten"


def mix_line(page: str) -> str:
    """The Schüttelwörter line of a page: the sentence's letters in another order."""
    key = sorted(SENTENCE.replace(" ", ""))
    lines = [line for line in page.splitlines() if sorted(line.replace(" ", "")) == key]
    lines = [line for line in lines if line != SENTENCE]
    assert len(lines) == 1, lines
    return lines[0]


def picture(data: bytes, page: int) -> bytearray:
    """The pixels of a page, with its bottom right corner (20 by 12 mm) made blank."""
    bitmap = pypdfium2.PdfDocument(data)[page].render(scale=2, rev_byteorder=True)
    per_mm = 2 * 72 / 25.4
    cut_x = bitmap.width - round(20 * per_mm)
    cut_y = bitmap.height - round(12 * per_mm)
    out = bytearray(bitmap.buffer)
    for row in range(cut_y, bitmap.height):
        start = row * bitmap.stride
        out[start + cut_x * 3 : start + bitmap.width * 3] = b"\0" * ((bitmap.width - cut_x) * 3)
    return out
