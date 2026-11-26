"""What issue #814 found in the brief's twenty-third run, where it is still open.

A click on an option of an open Zahlenraum is already settled: the brief says
`click "bis 100"` finds nothing and the keys choose, and test_635 and test_581 lock that.
"""

from test_teacher_run import section


def test_814_the_upright_swipe_opens_the_pages_from_the_left_edge():
    # Since #1187 the Format panel comes from below, and the right edge with its scrollbar opens nothing.
    bullet = next(
        line for line in section("## Rules").splitlines() if line.startswith("  - `swipe ")
    )
    assert "`swipe 10,600 200,600`" in bullet
    assert "800,600" not in bullet
    assert "`click Fertig`" in bullet


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


def test_814_the_tour_is_the_accounts_so_beenden_is_clicked_only_when_it_is_open():
    # The tour is remembered with the account: a teacher who closed it never sees Beenden again.
    how = section("## How the editor works")
    assert "with the account, not in the browser" in how
    assert '`click "Beenden"` then finds nothing' in how
    assert "Close it with `Beenden` only when it is open" in how
    step = next(line for line in section("## Two teachers").splitlines() if line.startswith("4. "))
    assert "only if this teacher has not closed it before" in step
    assert 'close it with `click "Beenden"` when it is open' in step


def test_814_two_read_only_where_verbs_are_two_shell_calls():
    # The run put two where verbs on one line. A read-only verb is still one call.
    rules = section("## Rules")
    assert "Two `where` calls in one shell call are two verbs" in rules
    assert "a read-only `where` or `value` included" in rules
    forbidden = rules.split("\nForbidden:\n", 1)[1]
    assert "another shell call of `where` alone" in forbidden
