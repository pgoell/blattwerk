"""What issue #536 found in the brief's ninth run."""

from test_teacher_run import section


def test_536_a_lineatur_and_a_table_name_their_font_and_their_trace():
    how = section("## How the editor works")
    assert "`Schriftart auf den Zeilen`" in how
    assert "`Schriftart der Tabelle`" in how
    assert "`Nachspurtext`" in how
    assert '`click "Schriftart"` finds nothing on a Lineatur or a table' in how
    assert '`click "Nachspurtext"`' in section("### 2. ")


def test_536_enter_after_the_choice_opens_the_blocks_text():
    how = section("## How the editor works")
    assert "another `key Enter` opens the block's text" in how


def test_536_drag_can_hold_and_right_click_opens_the_menu():
    rules = section("## Rules")
    assert "`drag FROM TO [SECONDS]`" in rules
    assert "at most 3" in rules
    assert "`right-click TARGET`" in rules
    assert "`Zellen verbinden`" in rules


def test_536_a_thumbnail_shows_its_hint_where_the_screenshot_can_see_it():
    how = section("## How the editor works")
    assert "A page thumbnail shows `Ziehen verschiebt die Seite`" in how
