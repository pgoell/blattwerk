"""What issue #635 found in the brief's fourteenth run, where it is still open."""

from test_teacher_run import section


def test_635_a_new_block_lands_under_the_lowest_and_the_picture_says_so():
    # The picture lands under the heading (#621). The notes still said it lands on top.
    how = section("## How the editor works")
    bullet = next(line for line in how.splitlines() if line.startswith("- A new block lands"))
    assert "under the lowest block" in bullet
    assert "5 mm below it" in bullet
    assert "at that block's left edge" in bullet
    assert "The first block on an empty page lands at the top, in the margin." in bullet
    assert "often on top of the one before" not in bullet
    assert "lands at the top of the page" not in bullet
    picture = next(line for line in section("### 3. ").splitlines() if line.startswith("3. "))
    assert "picked and under the heading" in picture
    assert "Put it at 40 mm: `fill` the field `Y` with `40`" in picture
    assert "on top of the heading" not in picture


def test_635_sheet_1_sets_zahlenraum_with_keys_and_reads_uebertrag():
    # A click on the option bis 100 did nothing, and value Übertrag found no field.
    step = next(line for line in section("### 1. ").splitlines() if line.startswith("4. "))
    assert '`click "Zahlenraum"`, `key ArrowDown`, `key Enter`' in step
    assert "`bis 20`" in step
    assert "`bis 100`" in step
    assert '`click "bis 100"` finds nothing' in step
    assert '`click "Mit"`' in step
    assert '`value "Übertrag"` prints `Mit`' in step
    how = section("## How the editor works")
    option = next(line for line in how.splitlines() if "an option of an open list" in line)
    assert '`click "bis 100"` finds nothing' in option


def test_635_a_folded_zoom_number_is_read_from_the_list():
    # At 820 wide and at 1000 by 800 the percent folds into Mehr, so where "%" finds nothing.
    listed = next(
        line for line in section("## Rules").splitlines() if line.startswith("  - `where NAME`")
    )
    assert "1000 by 800" in listed
    assert "folds into `Mehr`" in listed
    assert '`click "Mehr"`, `click "Zoom"`' in listed
    assert '`value "Zoom in Prozent"`' in listed


def test_635_plus_is_the_german_key_and_control_plus_zooms():
    listed = next(
        line for line in section("## Rules").splitlines() if line.startswith("  - `key KEYS")
    )
    assert "`+` is the German plus key" in listed
    assert "types + with no Shift" in listed
    assert '`key "Control++"` zooms in' in listed
    assert '`key "Control+NumpadAdd"`' in listed
    assert '`key "Control+Equal"`' in listed


def test_635_klassenarbeit_and_the_open_zoom_list_have_one_click():
    # where prints several, and the run clicked by pixels.
    rules = section("## Rules")
    assert '`click "Klassenarbeit"` takes the template' in rules
    assert "`Klassenarbeit Deckblatt`" in rules
    assert "turns the left panel to it" in rules
    assert 'With the zoom\'s list open, `click "Ganze Seite"` takes the list' in rules


def test_635_a_sheet_may_be_built_in_either_window():
    # The run built sheet 4 in the tool's window. The brief already allows either.
    assert "A sheet may be built in either window" in section("## The five sheets")
