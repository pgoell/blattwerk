"""A cut picture shows and prints what the cut left of it, and nothing of what it took."""

import io
import math

import pytest
from PIL import Image
from pixels import measures, screen_and_print
from playwright.sync_api import expect
from test_pixels import photo
from ui import at, box, expect_picked, pick, sheet, user

# Half cut off one side: the box's edge that the cut lies on and the way out of the box there, in
# shares of the box, then the colour channels that tell the field beyond the cut from the one that
# stays and from white, and how far apart they are in that field.
SIDES = {
    # Green stays and blue is cut off.
    "left": ((0, 0.25), (-1, 0), (2, 1), 88),
    # Orange stays and blue is cut off.
    "top": ((0.25, 0), (0, -1), (2, 1), 88),
    # Blue stays and green is cut off.
    "right": ((1, 0.25), (1, 0), (1, 2), 90),
    # Blue stays and orange is cut off.
    "bottom": ((0.25, 1), (0, 1), (0, 2), 240),
}
LOOKS = {
    "plain": {},
    "flipX": {"flipX": True},
    "flipY": {"flipY": True},
    "turned": {"angle": 90, "flipX": True},
}
# How many pixels of the field beyond the cut may show across an edge, in pictures of eight pixels
# to a millimetre. A box's clip on whole pixels let 1 to 1.3 through, in print and in Chromium.
# The pixel the cut runs through is a blend of both fields, half covered: 0.35 at most.
STRIP = 0.5


def cut(client, side, n, **more):
    """A picture with half cut off one side, each edge near the middle of a pixel of the print."""
    share = [0.5 if name == side else 0 for name in SIDES]
    w, h = (171.08, 228.08) if side in ("left", "right") else (342.08, 114.08)
    # In the print's pixels, 96 to an inch: there a box's clip went out to the next whole one.
    place = {"x": 82.46 + 359 * (n % 2), "y": 163.46 + 453 * (n // 2), "w": w, "h": h}
    place = {name: round(v * 25.4 / 96, 3) for name, v in place.items()}
    return box(side, "image", {**photo(client), "cut": share}, **place, **more)


def beyond(image, block, side):
    """How many pixels of the cut-off field's colour lie across the block's edge at the cut."""
    (u, v), (du, dv), (one, two), full = SIDES[side]
    k = image.width / 210
    # The page's point for a place in the box, in shares of it and millimetres out of it: a flip
    # mirrors the box in itself and a turn goes about its centre.
    u, du = (1 - u, -du) if block.get("flipX") else (u, du)
    v, dv = (1 - v, -dv) if block.get("flipY") else (v, dv)
    turn = math.radians(block.get("angle", 0))
    cos, sin = math.cos(turn), math.sin(turn)

    def pixel(out, along):
        x = (u - 0.5) * block["w"] + du * out - dv * along
        y = (v - 0.5) * block["h"] + dv * out + du * along
        centre = block["x"] + block["w"] / 2, block["y"] + block["h"] / 2
        return image.getpixel(
            (round((centre[0] + x * cos - y * sin) * k), round((centre[1] + x * sin + y * cos) * k))
        )

    found = 0
    # From 3 mm inside the edge to 3 mm outside, pixel by pixel: each the mean of nine along it.
    for step in range(-24, 25):
        row = [pixel(step / 8, along / 2) for along in range(-4, 5)]
        found += max(0, sum(p[one] - p[two] for p in row) / len(row)) / full
    return found


@pytest.mark.parametrize("look", LOOKS)
def test_nothing_of_the_cut_off_part_shows_or_prints(browser, server, look):
    client = user()
    page = [cut(client, side, n, **LOOKS[look]) for n, side in enumerate(SIDES)]
    mine = sheet(client, page)["id"]
    screen, printed = (
        Image.open(io.BytesIO(data)).convert("RGB")
        for data in screen_and_print(browser, server, client, mine)
    )
    found = {
        f"{side} {name}": round(beyond(image, block, block["id"]), 2)
        for block, side in zip(page, SIDES, strict=True)
        for name, image in (("screen", screen), ("print", printed))
    }
    assert max(found.values()) < STRIP, found


def test_a_cut_and_flipped_picture_shows_its_corners_as_they_print(browser, server):
    """A6"""
    client = user()
    # A quarter cut off the left and half off the bottom, as the page "pictures" of test_pixels.py
    # has it: flipped, the blue field lies over the orange one that is cut off.
    props = {**photo(client), "cut": [0.25, 0, 0, 0.5]}
    looks = [{"flipY": True}, {"flipX": True}, {"flipX": True, "flipY": True}]
    page = [
        box(f"b{n}", "image", props, x=45, y=30 + 50 * n, w=90, h=40, **look)
        for n, look in enumerate(looks)
    ]
    page.append(box("turned", "image", props, x=60, y=205, w=90, h=40, flipX=True, angle=30))
    whole = {**props, "cut": [0, 0, 0, 0]}
    page.append(box("whole", "image", whole, x=150, y=30, w=45, h=30, flipX=True, flipY=True))
    found, _ = measures(*screen_and_print(browser, server, client, sheet(client, page)["id"]))
    # A strip of the orange field under the blue one was 0.34 of a tile's blue ink.
    assert found["ink"][0] < 0.25, found


def test_a_click_on_the_cut_off_part_picks_nothing(editor):
    client = user()
    page = editor(cut(client, "left", 1), client=client)
    place = at(page, "left").bounding_box()
    # The whole picture is twice as wide as the block and reaches as far to the left of it.
    page.mouse.click(place["x"] - place["width"] / 2, place["y"] + place["height"] / 2)
    expect_picked(page)
    page.mouse.click(place["x"] + 5, place["y"] + place["height"] / 2)
    expect_picked(page, "left")


def test_a_cut_and_flipped_picture_crops_in_its_frame(editor):
    client = user()
    page = editor(cut(client, "left", 1, flipX=True), client=client)
    pick(page, "left")
    was = at(page, "left").bounding_box()
    page.get_by_role("button", name="Zuschneiden").click()
    frame = page.locator(".crop > div")
    expect(frame).to_have_count(1)
    now = frame.bounding_box()
    for side in ("x", "y", "width", "height"):
        assert now[side] == pytest.approx(was[side], abs=1), (was, now)
    # Mirrored, the half that is cut off lies to the block's right.
    whole = page.locator(".crop").bounding_box()
    assert whole["x"] == pytest.approx(was["x"], abs=1)
    assert whole["width"] == pytest.approx(2 * was["width"], abs=1)
