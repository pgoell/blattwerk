"""The hand experiment for issue 94: ten pictures, and the upload that already prints them.

The record is the result. The numbers are read back from the files, so a written darkness cannot
drift from the JPEG it names.
"""

import json
from pathlib import Path

import httpx
import pypdfium2
from PIL import Image
from ui import sheet, user

ROOT = Path(__file__).parents[1]
DIR = ROOT / "docs" / "experiments" / "94-wasserkreislauf"
RECORD = DIR / "record.json"
# Near black, as a stroke that should survive a copy. Paper is what a copier leaves blank.
BLACK = 30
PAPER = 245


def measured(path):
    """Ink, paper, and whether the file is a line drawing a copier can keep.

    One black pixel is not enough, and a downscale hides a thin stroke, so the shares are of the
    file itself. A channel gap past 8 is colour. JPEG noise on these files stays under that.
    A drawing with less than half a percent of ink has no line. One that covers more than a tenth
    of the square, or leaves under nine tenths paper, is a filled mass, not a picture to label.
    """
    image = Image.open(path)
    rgb = image.convert("RGB")
    raw = rgb.tobytes()
    width = rgb.width
    row_bytes = width * 3
    gap = 0
    for y in range(0, rgb.height, 8):
        start = y * row_bytes
        for x in range(0, width, 8):
            i = start + x * 3
            red, green, blue = raw[i], raw[i + 1], raw[i + 2]
            gap = max(gap, abs(red - green), abs(green - blue), abs(red - blue))
    hist = image.convert("L").histogram()
    total = sum(hist)
    darkest = next(i for i, count in enumerate(hist) if count)
    ink = sum(hist[:BLACK]) / total
    paper = sum(hist[PAPER:]) / total
    # Line on paper: black exists, the square is mostly paper, the ink is not a filled mass.
    line = darkest <= BLACK and 0.005 <= ink <= 0.10 and paper >= 0.90 and gap <= 8
    return {
        "darkest": darkest,
        "ink": round(ink, 4),
        "paper": round(paper, 4),
        "channelGap": gap,
        "lineOnPaper": line,
    }


def load():
    return json.loads(RECORD.read_text())


def test_the_experiment_record_names_ten_pictures():
    record = load()
    assert record["topic"] == "Wasserkreislauf"
    assert record["verdict"] in ("yes", "no", "limits")
    assert isinstance(record["askedTheFirstUser"], bool)
    assert isinstance(record["open"], list)
    pictures = record["pictures"]
    assert len(pictures) == 10
    seen = set()
    for picture in pictures + record["discarded"]:
        assert picture["file"] not in seen
        seen.add(picture["file"])
        path = DIR / picture["file"]
        assert path.read_bytes().startswith(b"\xff\xd8\xff")
        assert picture["prompt"]
        assert picture["model"]
        assert picture["tries"] >= 1
        assert picture["cost"]
        assert isinstance(picture["errors"], list)
        assert isinstance(picture["reported"], list)
        assert measured(path) == {
            "darkest": picture["darkest"],
            "ink": picture["ink"],
            "paper": picture["paper"],
            "channelGap": picture["channelGap"],
            "lineOnPaper": picture["lineOnPaper"],
        }
    assert record["terms"]
    for term in record["terms"]:
        assert term["model"]
        assert term["read"]
    assert record["costGuess"]["notMeasured"] is True


def test_the_experiment_pictures_print_through_the_upload(server):
    """The issue asks to put the pictures on a sheet through the upload that exists, and print."""
    record = load()
    # The heaviest keeper and the lightest: a filled drawing and a thin one, on one sheet.
    darkest = max(record["pictures"], key=lambda picture: picture["ink"])
    palest = min(record["pictures"], key=lambda picture: picture["ink"])
    assert darkest["file"] != palest["file"]
    client = user()
    ids = {}
    for picture in (darkest, palest):
        data = (DIR / picture["file"]).read_bytes()
        res = client.post("/api/uploads", files={"file": (picture["file"], data, "image/jpeg")})
        assert res.status_code == 200, picture["file"]
        assert res.json()["id"]
        ids[picture["file"]] = res.json()["id"]
    blocks = [
        {
            "id": "dark",
            "type": "image",
            "x": 20,
            "y": 40,
            "w": 80,
            "h": 80,
            "z": 1,
            "locked": False,
            "props": {"upload": ids[darkest["file"]], "ratio": 1, "cut": [0, 0, 0, 0]},
        },
        {
            "id": "pale",
            "type": "image",
            "x": 110,
            "y": 40,
            "w": 80,
            "h": 80,
            "z": 2,
            "locked": False,
            "props": {"upload": ids[palest["file"]], "ratio": 1, "cut": [0, 0, 0, 0]},
        },
    ]
    mine = sheet(client, blocks, title="Wasserkreislauf")
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{mine['id']}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    scale = 2
    bitmap = pypdfium2.PdfDocument(res.content)[0].render(scale=scale, rev_byteorder=True)

    def at(mm):
        return int(mm * scale * 72 / 25.4)

    def pixel(x, y):
        start = at(y) * bitmap.stride + at(x) * bitmap.n_channels
        return bytes(bitmap.buffer[start : start + 3])

    def box_darkest(x, y, w, h):
        """The darkest channel inside the box. A grid can miss a thin stroke."""
        x0, y0, x1, y1 = at(x), at(y), at(x + w), at(y + h)
        seen = 255
        channels = bitmap.n_channels
        for row in range(y0, y1):
            start = row * bitmap.stride + x0 * channels
            row_bytes = bytes(bitmap.buffer[start : start + (x1 - x0) * channels])
            seen = min(seen, min(row_bytes))
        return seen

    # The margin is paper. A picture that failed to print would leave its box the same white.
    assert min(pixel(5, 5)) > 240
    for picture, x0 in ((darkest, 20), (palest, 110)):
        assert box_darkest(x0, 40, 80, 80) < 220, picture["file"]
