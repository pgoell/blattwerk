"""What issue #617 found in the brief's thirteenth run, where it is still open."""

from test_teacher_run import BRIEF, section


def test_617_the_minutes_come_from_the_tools_clock_not_the_shell_date():
    # The run timed itself with `date`, and that clock ran slow against the work.
    order = next(part for part in BRIEF.split("\n\n") if part.startswith("Time: "))
    assert "The minutes are the work's." in order
    assert "The shell's `date` can run slow against the work" in order
    assert "it does not time a part" in order
    assert "`The clock is N`" in order
    assert "the seconds since `start`" in order
    assert "Run `date` at the start" not in order
    step = next(line for line in section("## 25 minutes").splitlines() if line.startswith("1. "))
    assert "not with `date`" in step
    assert "the shell's `date` can run slow against the work" in step
    assert "Stop after 25 minutes, wherever you are, and not before" in step
    assert "stop after 30 minutes instead, wherever you are, and not before" in step
    assert "nor at any minute short of 30" in step
    report = next(line for line in section("## Report").splitlines() if line.startswith("6. "))
    assert "`The clock is N`" in report
    assert "not from the shell's `date`" in report
    rules = section("## Rules")
    assert "The line before it is `The clock is N`" in rules
    assert "the minutes come from this clock and not from `date`" in rules
    sign_in = section("## Sign in")
    assert "`date +%s`" in sign_in
    assert "That number only names the context." in sign_in


def test_617_an_umlaut_is_a_keydown_and_a_pdf_click_saves_the_file():
    rules = section("## Rules")
    key = next(line for line in rules.splitlines() if line.startswith("  - `key KEYS"))
    assert '`key "Ä"`' in key
    typed = next(line for line in rules.splitlines() if line.startswith("  - `type TEXT`"))
    assert "`Ü`" in typed
    assert "a picked block opens on it" in typed
    assert '`type "Übung"`' in typed
    pdf = next(line for line in rules.splitlines() if line.startswith("  - `pdf [TARGET]`"))
    assert '`click "PDF"` and `click "Lösungen"` do the same' in pdf
    assert "not left in Downloads" in pdf
    assert "take that dialog's button, not the bar's of the same name" in pdf
