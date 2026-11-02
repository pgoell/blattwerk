"""What issue #814 found in the brief's twenty-third run, where it is still open.

A click on an option of an open Zahlenraum is already settled: the brief says
`click "bis 100"` finds nothing and the keys choose, and test_635 and test_581 lock that.
"""

from test_teacher_run import section


def test_814_the_upright_swipe_starts_clear_of_the_scrollbar():
    # 817 lies on the scrollbar of the upright window. 800 starts the swipe.
    bullet = next(
        line for line in section("## Rules").splitlines() if line.startswith("  - `swipe ")
    )
    assert "`swipe 800,600 660,600`" in bullet
    assert "817,600" not in bullet
    assert "x 817 lies on the scrollbar" in bullet


def test_814_a_photograph_reaches_the_run_folder_by_a_verb():
    # The shell cannot copy a photograph in, so the upload used the drawn PNG.
    rules = section("## Rules")
    bullet = next(line for line in rules.splitlines() if line.startswith("  - `photo`"))
    assert "photo.jpg" in bullet
    assert "needs no window" in bullet
    assert '`upload photo.jpg "Bild"`' in bullet
    assert "drawn PNG" in bullet
    sheet = next(line for line in section("### 3. ").splitlines() if line.startswith("1. "))
    assert "drawn PNG" in sheet
    assert "`photo`" in sheet
    assert "photo.jpg" in sheet
    assert "This sheet uses the drawn file" in sheet


def test_814_click_can_repeat_so_quick_maths_clicks_are_one_call():
    # One verb per call cannot click fast enough for two maths clicks (#794).
    bullet = next(
        line for line in section("## Rules").splitlines() if line.startswith("  - `click ")
    )
    assert "`click TARGET [N]`" in bullet
    assert '`click "Eine Aufgabe mehr" 2`' in bullet
    assert "#794" in bullet


def test_814_the_second_teacher_gets_no_tour_in_the_same_window():
    # The tour is remembered in the browser, so the second teacher never sees Beenden.
    how = section("## How the editor works")
    assert "not per teacher" in how
    assert "the same window" in how
    assert '`click "Beenden"` then finds nothing' in how
    step = next(line for line in section("## Two teachers").splitlines() if line.startswith("4. "))
    assert "same window" in step
    assert "do not click it" in step
    assert '`click "Beenden"` finds nothing' in step


def test_814_two_read_only_where_verbs_are_two_shell_calls():
    # The run put two where verbs on one line. A read-only verb is still one call.
    rules = section("## Rules")
    assert "Two `where` calls in one shell call are two verbs" in rules
    assert "a read-only `where` or `value` included" in rules
    forbidden = rules.split("\nForbidden:\n", 1)[1]
    assert "another shell call of `where` alone" in forbidden
