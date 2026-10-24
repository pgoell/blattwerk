"""What the teacher-page tool refuses, and how a verb finds the one control it names."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import subprocess

import pytest
from test_teacher_page import (
    ONE,
    folder,  # noqa: F401
    middle,
    pytestmark,  # noqa: F401
    run,
    tool,
)
from ui import (
    TEXT,
    at,
    box,
    expect_picked,
)

# What the tool refuses


def test_click_refuses_a_name_that_is_not_on_the_page(editor):
    page = editor(box("a", "text", ONE))
    with pytest.raises(tool.Refused, match='nothing on the page is called "Drei"'):
        tool.click(page, "Drei")
    expect_picked(page)


def test_click_refuses_a_name_that_is_there_twice_and_lists_the_places(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    places = [middle(at(page, name).get_by_text("Hallo")) for name in "ab"]
    with pytest.raises(tool.Refused) as refused:
        tool.click(page, "Hallo")
    assert str(refused.value) == (
        f'"Hallo" is on the page 2 times, at {places[0]}, {places[1]}: give one as X,Y'
    )
    expect_picked(page)
    # One of the listed places is a target.
    tool.click(page, places[1])
    expect_picked(page, "b")


@pytest.mark.parametrize(
    "words, said",
    [
        (["click", "PDF"], "no page is running: start it first, with the verb `start`\n"),
        (["click"], "click takes: TARGET\n"),
        (["press", "Enter"], 'no verb "press": there are start, stop, open, click'),
        ([], 'no verb "": there are start, stop, open, click'),
    ],
)
def test_the_command_line_refuses_in_plain_words_and_fails(folder, server, words, said):
    done = run(folder, server, *words)
    assert done.returncode == 1 and done.stdout == ""
    assert done.stderr.startswith(said) and "Traceback" not in done.stderr


def test_stop_with_nothing_running_says_so_and_is_no_failure(folder, server):
    done = run(folder, server, "stop")
    assert (done.returncode, done.stdout, done.stderr) == (0, "no page was running\n", "")


def test_stop_leaves_a_process_alone_that_only_has_the_holders_pid(folder, server):
    # The holder died without `stop` and the system gave its pid to someone else.
    other = subprocess.Popen(["sleep", "60"])
    (folder / "page.json").write_text(f'{{"pid": {other.pid}, "group": {other.pid}}}')
    done = run(folder, server, "stop")
    assert (done.returncode, done.stdout, done.stderr) == (0, "no page was running\n", "")
    assert other.poll() is None
    other.kill()
    other.wait()


def test_stop_takes_a_file_that_names_no_holder_for_nothing_running(folder, server):
    (folder / "page.json").write_text("{")
    done = run(folder, server, "stop")
    assert (done.returncode, done.stdout, done.stderr) == (0, "no page was running\n", "")
