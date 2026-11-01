"""What issue #681 found in the brief's sixteenth run, where it is still open."""

from test_teacher_run import PRS, section


def test_681_an_above_all_hunt_uses_every_minute_of_the_30():
    # The run stopped at about 21 minutes. The brief already says not to.
    prs = section(PRS)
    assert "stop after 30 minutes instead, wherever you are, and not before" in prs
    assert "nor at any minute short of 30" in prs


def test_681_a_web_passage_comes_from_the_stages_datenschutz():
    # The live site is barred, so the run copied from /datenschutz with no line that says to.
    how = section("## How the editor works")
    assert "the live site is barred" in how
    assert "`open /datenschutz`" in how
    assert "`key Control+a`" in how
    assert "`key Control+c`" in how
    assert "`key Control+v`" in how


def test_681_the_window_can_ctrl_click_hold_a_finger_paste_word_and_record():
    rules = section("## Rules").split("\nForbidden:\n")[0]
    assert "  - `ctrl-click TARGET`" in rules
    assert "adds that page to the choice" in rules
    assert '`where "Seite 3"`' in rules
    assert "  - `finger TARGET`" in rules
    assert "held still" in rules
    assert "  - `paste-word TEXT`" in rules
    assert "`*fett*`" in rules
    assert "`_schief_`" in rules
    assert "  - `drop-web FILE TARGET`" in rules
    assert "fetches nothing" in rules
    assert "  - `mic`:" in rules
    assert "MCP page has none" in rules
    how = section("## How the editor works")
    assert "`ctrl-click X,Y`" in how
    assert "`finger X,Y`" in how
    assert '`paste-word "Ein *fett* Wort"' in how
    assert "`drop-web bild.png X,Y`" in how
    assert "`mic`" in how
