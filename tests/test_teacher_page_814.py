"""The teacher-page tool for issue #814: a photograph, and a click that repeats."""

# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

from playwright.sync_api import expect
from test_maths_foot import height, tasks
from test_teacher_page import (
    folder,  # noqa: F401
    pytestmark,  # noqa: F401
    run,
    tool,
)
from ui import box, maths, pick, saved, user


def test_photo_copies_a_real_photograph_into_the_run_folder(folder, server):
    done = run(folder, server, "photo")
    assert done.returncode == 0 and done.stderr == ""
    dest = folder / "photo.jpg"
    assert done.stdout == f"{dest}\n"
    raw = dest.read_bytes()
    assert raw[:3] == b"\xff\xd8\xff"
    assert raw == tool.PHOTO.read_bytes()
    assert run(folder, server, "photo", "extra").returncode == 1


def test_click_takes_a_repeat_count(folder, server):
    # Before the count existed, the line refused a second argument.
    done = run(folder, server, "click", "Eine Aufgabe mehr", "2")
    assert done.returncode == 1 and done.stdout == ""
    assert done.stderr.startswith("no page is running")
    assert "takes:" not in done.stderr


def test_click_n_times_is_n_quick_clicks_on_eine_aufgabe_mehr(editor):
    # Two calls are two steps. One call clicks twice before either answer lands (#794).
    client = user()
    props = maths(client, ops=["+"], max=20, count=4, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=20, h=height(props)), client=client)
    pick(page, "m")
    expect(tasks(page).first).to_have_text("4 Aufgaben")
    posts = []

    def count(route):
        posts.append(route)
        route.fallback()

    page.route("**/api/maths", count)
    said = tool.click(page, "Eine Aufgabe mehr", "2")
    assert " 2 times" in said
    assert len(posts) == 2
    saved(page, client)
    expect(tasks(page).first).to_have_text("6 Aufgaben")
    assert saved(page, client)[0]["props"]["count"] == 6
