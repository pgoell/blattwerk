"""What later issues asked the teacher-run brief to say, and the lines it keeps."""

import json
import re
import subprocess

from test_teacher_run import BRIEF, MISE, PRS, REPO, on_screen, section

# What issue #406 found in the brief's fourth run, 1 to 11. Point 1 is a test of the tool.


def test_406_2_sheet_4_sets_the_title_in_the_window_that_built_the_sheet():
    sheet4 = section("### 4. ")
    mcp, built_in_tool = sheet4.split("- built in the tool's window:")
    assert "- built in the MCP page:" in mcp
    assert "`type_text` `TR4 Zwei Seiten`" in mcp
    tool_title = '`click "Titel"`, `key Control+a`, `type "TR4 Zwei Seiten"`, `key Enter`'
    assert tool_title in built_in_tool
    assert "`fill`" not in sheet4


def test_406_3_a_control_below_the_window_is_clicked_and_the_tool_turns_the_panel():
    how = section("## How the editor works")
    lines = how.splitlines()
    bullet = next(line for line in lines if line.startswith("  - a control of the right panel"))
    assert "below the window's lower edge" in bullet
    assert "the tool turns the panel to it" in bullet
    assert "`wheel` is needed only for a point given as `X,Y`" in bullet
    source = "\n".join(p.read_text() for p in sorted((REPO / "frontend/src").rglob("*.tsx")))
    for label in ("Randstärke", "Jedes n-te Wort", "Lösungswörter"):
        assert f"`{label}`" in bullet, label
        assert on_screen(label, source), label


def test_406_4_a_snapshot_is_searched_in_its_file_with_the_grep_tool():
    allowed = section("## Rules").split("\nForbidden:\n")[0]
    grep = "- `grep` in the shell, on a snapshot file in `/tmp/teacher-run` and on nothing else."
    assert grep in allowed
    assert "There is no Grep tool." in allowed
    assert "`take_snapshot` with its `filePath` `/tmp/teacher-run/" in allowed
    assert "do not search that answer" in allowed


def test_406_5_the_jq_leaves_out_the_types_a_teacher_cannot_see_before_five_are_taken():
    prs = section(PRS)
    commands = re.findall(r"gh pr list [^\n]*--jq '(.+)'$", prs, re.M)
    assert len(commands) == 3
    # Sixteen merged pull requests, newest first. The ones that are no teacher's: 1, 3, 5, 7, 9, 10.
    titles = [
        "ci(deps): bump a runner",
        "feat: a word",
        "docs: the readme",
        "fix: a line",
        "chore: bump",
        "perf: a list",
        "test: a case",
        "feat(ui): a panel",
        "build: a script",
        "refactor: a helper",
        "fix!: a page",
        "feat: a word",
        "perf: a sum",
        "fix: a box",
        "feat: a bank",
        "fix: a tab",
    ]
    merged = [
        {
            "number": n + 1,
            "title": title,
            "url": f"https://github.com/pgoell/blattwerk/pull/{n + 1}",
            "body": "a body",
            "mergedAt": f"2026-10-{30 - n:02d}T10:00:00Z",
        }
        for n, title in enumerate(titles)
    ]
    listed = []
    for command in commands:
        out = subprocess.run(
            ["jq", "-r", command],
            input=json.dumps(merged),
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        listed.append([int(n) for n in re.findall(r"^#(\d+) ", out, re.M)])
    # The third list is the `test` titles the first two leave out (#497): number 7.
    assert listed == [[2, 4, 6, 8, 11], [12, 13, 14, 15, 16], [7]]


def test_406_7_a_delete_in_the_mcp_page_is_answered_with_handle_dialog():
    para = next(line for line in BRIEF.splitlines() if line.startswith("Which window for what."))
    delete = "A delete in the MCP page (a button whose name ends in `löschen`) opens a browser box"
    assert delete in para
    assert "answer it with `handle_dialog`" in para
    assert "`handle_dialog`" in section("## Rules").split("\nForbidden:\n")[0]


def test_406_9_tidy_is_the_last_command_and_the_herdr_line_follows_it():
    clean = section("## Clean up")
    assert clean.rindex(f"{MISE} teacher:page -- tidy") < clean.index("`herdr` line")
    assert "very last command before the `herdr` line" in clean
    assert "the `herdr` line that the orchestrator's prompt gives you" in clean


def test_406_10_the_above_all_split_still_adds_up_to_50_minutes():
    split = next(part for part in BRIEF.split("\n\n") if "above all" in part)
    assert "five sheets get 10 minutes, not 15" in split
    assert "build sheets 1, 3 and 4 only" in split
    assert "pull requests get 30 minutes, not 25" in split
    assert "at least 20 of the 30 minutes" in split
    assert "Issues and clean up keep 7" in split
    sheets = re.search(r"sheets get (\d+) minutes", split)
    pulls = re.search(r"pull requests get (\d+) minutes", split)
    issues = re.search(r"clean up keep (\d+)", split)
    assert sheets and pulls and issues
    # The start takes 3, as the time box above says.
    assert "Start and sign in take 3" in BRIEF
    assert 3 + int(sheets[1]) + int(pulls[1]) + int(issues[1]) == 50
    # Step 1 of the pull requests says the same stop: 30 minutes with an "above all".
    step = next(line for line in section(PRS).splitlines() if line.startswith("1. Note the time"))
    assert "stop after 30 minutes instead, wherever you are, and not before" in step
    assert "nor at any minute short of 30" in step


def test_406_11_a_gap_of_two_words_has_its_steps():
    how = section("## How the editor works")
    bullet = next(line for line in how.splitlines() if line.startswith("- A gap of two words"))
    assert "`key Home`" in bullet
    assert "`key Control+Shift+ArrowRight 2`" in bullet
    assert '`click "Lücke"`' in bullet


# What the teacher run's pull request #430 asks: the brief says what is true of the tool, the
# windows and the shell.


def test_t1_click_takes_the_only_control_of_a_name():
    assert "the only control of that name (a button, a field, a list or a tab)" in section(
        "## Rules"
    )


def test_t2_where_takes_a_name_with_a_slash():
    listed = next(line for line in BRIEF.splitlines() if line.startswith("  - `where NAME`"))
    assert 'A name with a slash, as `where "/ 7"`, works.' in listed


def test_t3_a_list_is_found_by_its_label_only():
    listed = next(line for line in BRIEF.splitlines() if line.startswith("  - `where NAME`"))
    assert "A list is found by its label only, never by its options" in listed


def test_t4_the_bar_paste_works_in_the_tools_window():
    assert "The bar's `Einfügen` works in the tool's window too." in section("## Rules")


def test_t5_a_control_outside_the_window_is_turned_to_by_the_tool():
    rules = section("## Rules")
    assert "its output ends with `(turned the page to it)`" in rules
    assert "`where` changes nothing and still says `(outside the window)`" in BRIEF


def test_t6_a_click_on_a_greyed_control_says_so():
    assert "clicked at X,Y, on a greyed control: nothing happens" in section("## Rules")


def test_t7_every_verb_output_names_the_page():
    assert "Every verb's output ends with a line `The page is /blatt/12`" in section("## Rules")


def test_t8_tidy_deletes_the_pdfs_in_the_run_folder():
    assert "and each PDF in `/tmp/teacher-run`, and names each one it deleted" in section(
        "## Rules"
    )


def test_d1_no_grep_tool_is_named():
    assert "There is no Grep tool." in section("## Rules")


def test_d2_pdftoppm_resolution_and_pdffonts():
    assert "`pdftoppm` takes `-r` from 60 to 110" in section("## Rules")
    assert "`pdffonts` names the fonts of a PDF." in section("## Rules")
    assert "To check the font, run `pdffonts` on the PDF before the `rm`." in section(
        "## Export and compare"
    )


def test_d3_screenshot_name_pattern():
    assert (
        "NAME takes letters, digits, `_`, commas and `-` only: no spaces and no dots."
        in section("## Rules")
    )


def test_d4_no_own_script_and_no_sleep():
    assert "A script of your own that wraps the tool, and `sleep`." in section("## Rules")


def test_d5_the_zoom_has_no_100_percent():
    assert "The zoom has no 100 %: its steps are 77, 88, 110 and 138 %." in section(
        "## Export and compare"
    )


def test_d6_the_tour_opens_once_per_device():
    how = section("## How the editor works")
    assert "opens the first time the editor opens on a device" in how
    assert "click `Rundgang` in the bar" in how


def test_d7_a_sheet_may_be_built_in_either_window():
    assert "A sheet may be built in either window" in section("## The five sheets")
    assert '`click "Y"`, `key Control+a`, `type "40"`, `key Enter`' in section(
        "## How the editor works"
    )


def test_d8_escape_after_a_list_unpicks_the_block():
    how = section("## How the editor works")
    assert (
        "After a choice from a list (`Zahlenraum`), do not press Escape: it unpicks the block."
        in how
    )
    assert "`End` goes to its last entry, which for `Zahlenraum` is `Eigener`" in how


def test_d9_gespeichert_may_be_the_old_one():
    assert "A `Gespeichert` read right after a change may be the old one" in section(
        "## How the editor works"
    )


def test_d10_a_turn_to_the_wrong_place_is_undone_with_escape():
    assert "press Escape to unpick the block and try again" in section("## Rules")


def test_d12_above_all_stops_at_30_minutes():
    step = next(line for line in section(PRS).splitlines() if line.startswith("1. Note the time"))
    assert "stop after 30 minutes instead, wherever you are, and not before" in step
    assert "nor at any minute short of 30" in step


def test_d13_a_long_wait_for_answer_is_read_from_a_file():
    how = section("## How the editor works")
    assert "On a sheet with a Lernwörter list, that answer is very long" in how
    assert "`take_snapshot` with a `filePath` writes the page to a file" in how


def test_758_1_the_stage_names_two_teachers_and_the_brief_pastes_across_them():
    start = section("## Start the stage")
    assert "Its last five lines are" in start
    assert "E-Mail: teacher-run@stage.invalid" in start
    assert "E-Mail: teacher-run-2@stage.invalid" in start
    two = section("## Two teachers")
    steps = ["`key Control+c`", '`click "Abmelden"`', "teacher-run-2@stage.invalid", "`open /`"]
    at = [two.index(step) for step in steps]
    assert at == sorted(at)
    # Each way a teacher pastes, the other app's field too.
    for way in ("`key Control+v`", '`click "Einfügen"`', "`paste-elsewhere`"):
        assert way in two, way


def test_758_2_the_brief_drops_a_file_from_the_run_folder():
    assert "`drop FILE TARGET`" in section("## Rules")
    assert "`drop bild.png X,Y`" in section("## How the editor works")


def test_758_4_the_brief_says_how_a_pdf_comes_while_the_clash_bar_waits():
    rules = section("## Rules")
    assert '`pdf "Andere Version laden"` or `pdf "Mit dieser überschreiben"`' in rules


def test_758_5_after_a_sign_in_the_window_stays_where_it_was():
    how = section("## How the editor works")
    assert "After any sign in, the window stays on the path it showed" in how
    assert "stays on `/konto`" in how


def test_758_6_the_mcp_page_opens_in_a_context_of_its_own_for_each_run():
    sign_in = section("## Sign in")
    assert "`date +%s`" in sign_in
    assert "`isolatedContext` `teacher-run-N`" in sign_in


# What issue #497 found in the brief's eighth run.


def test_497_a_test_title_is_read_because_it_can_change_the_app():
    prs = section(PRS)
    assert "A title that starts with `test` can still change the app, as #480 did" in prs
    assert "`gh pr view N -R pgoell/blattwerk --json title,body`" in prs
    assert "Try a claim a teacher can see, and skip one that changes nothing a teacher sees." in prs


def test_497_a_claim_clicks_cannot_try_is_not_a_fault_of_the_app():
    prs = section(PRS)
    assert "a claim you cannot try with clicks and keys is not a fault of the app" in prs
    assert "A block type the app does not offer" in prs


def test_497_stacked_blocks_show_nothing_about_ink():
    prs = section(PRS)
    assert "shows nothing about ink, line spacing or a font" in prs
    assert "move them apart on the screen and in the PDF before you judge" in prs


def test_497_the_brief_names_the_dialog_pdf_and_the_offscreen_list():
    rules = section("## Rules")
    assert '`click "Aufgabenfamilien"` turns the panel to the list' in rules
    assert "take that dialog's button, not the bar's of the same name" in rules


def test_497_an_above_all_uses_every_minute_of_the_30():
    # The eighth run stopped at 27. "do not stop at 25" still allowed every minute short of 30.
    step = next(line for line in section(PRS).splitlines() if line.startswith("1. Note the time"))
    assert "stop after 30 minutes instead, wherever you are, and not before" in step
    assert "nor at any minute short of 30" in step


def test_497_sheet_2_clicks_the_one_seitenbreite():
    # The zoom's button was Seitenbreite. #623 named it Zoom, and the brief still said the zoom
    # had a button of that name, so the run treated the one panel button as two matches.
    sheet2 = section("### 2. ")
    assert "the zoom has a button of the same name" not in sheet2
    assert "the zoom's own button is `Zoom`" in sheet2
    assert "only while the list is open" in sheet2
    source = "\n".join(p.read_text() for p in sorted((REPO / "frontend/src").rglob("*.tsx")))
    assert on_screen("Zoom", source)


def frontend():
    """The editor's source, joined, for a name a teacher can read on screen."""
    return "\n".join(p.read_text() for p in sorted((REPO / "frontend/src").rglob("*.tsx")))


# What issue #564 found in the brief's tenth run.


def test_564_thumbnails_are_under_vorlagen_and_the_badge_opens_nothing():
    # The run used the Vorlagen tab to reach the thumbnails for Ctrl+arrow, and the badge
    # "Seite 2 von 3" opened nothing. Start has no thumbnails. The badge is a label.
    how = section("## How the editor works")
    bullet = next(line for line in how.splitlines() if line.startswith("- The page thumbnails"))
    assert "tab `Vorlagen`" in bullet
    assert "heading `Seiten`" in bullet
    assert "has no thumbnails" in bullet
    assert "`key Control+ArrowDown`" in bullet
    assert "`key Control+ArrowUp`" in bullet
    assert "`key Control+Shift+ArrowDown`" in bullet
    assert "`key Control+Shift+ArrowUp`" in bullet
    assert "badge `Seite 2 von 3`" in bullet
    assert "a click on it opens nothing" in bullet
    assert "`Seiten und Vorlagen`" in bullet
    source = frontend()
    for label in ("Vorlagen", "Seiten"):
        assert on_screen(label, source), label
    stage = (REPO / "frontend/src/pages/editor/Stage.tsx").read_text()
    badge = re.search(r'<div className="dock at">.*?</div>', stage, re.S)
    assert badge, stage
    assert "<button" not in badge.group(0)
    assert "onClick" not in badge.group(0)


def test_564_a_double_click_opens_a_zahlenmauer_stone_on_the_sheet():
    # #563 fixed the stone. The brief still names a text, a cell and a Lineatur, so a run
    # types into the panel's small wall.
    how = section("## How the editor works")
    bullet = next(line for line in how.splitlines() if "A double click opens" in line)
    assert "a stone of a Zahlenmauer" in bullet
    assert "small wall in the right panel" in bullet
    # F2 opens a text, a cell or a Lineatur. It does not open a stone.
    assert "F2" not in bullet.split("Zahlenmauer", 1)[1]
    assert 'label: "Zahlenmauer"' in (REPO / "frontend/src/pages/editor/useTools.tsx").read_text()


def test_564_a_table_has_no_drehung_and_stays_level():
    # Drehung is greyed on a table, so the run made no turned table with cut lines.
    how = section("## How the editor works")
    bullet = next(
        line for line in how.splitlines() if line.startswith("- A table has no `Drehung`")
    )
    assert "greyed" in bullet
    assert "not a fault" in bullet
    assert "`Schneidelinien`" in bullet
    assert "level table" in bullet
    assert "turned table with cut lines cannot be made" in bullet
    place = (REPO / "frontend/src/pages/format/place.tsx").read_text()
    turns = re.findall(r'"(Rechtsdrehung[^"]*|Linksdrehung[^"]*)"', place)
    assert turns
    for name in turns:
        assert f"`{name}`" in bullet, name
    level = next(line for line in place.splitlines() if line.strip().startswith("const level"))
    assert 'b.type === "table"' in level
    assert "disabled={level}" in place
    source = frontend()
    for label in ("Drehung", "Schneidelinien"):
        assert on_screen(label, source), label


# What issue #581 found in the brief's eleventh run.


def test_581_key_drag_holds_a_key_and_space_pans_the_desk():
    # The run tapped Space. A held Space while dragging pans, and a tap leaves the desk.
    rules = section("## Rules")
    bullet = next(line for line in rules.splitlines() if line.startswith("  - `key-drag "))
    assert "`key-drag KEY FROM TO`" in bullet
    assert "holds `KEY` down" in bullet
    assert "`key-drag Space X,Y X2,Y2`" in bullet
    assert "pans the desk" in bullet
    assert "`key Space` leaves the desk where it is" in bullet


def test_581_a_pixel_on_an_open_list_option_is_not_a_choice():
    # A click at X,Y on an option of an open list did nothing. The run then used the keys.
    how = section("## How the editor works")
    bullet = next(
        line for line in how.splitlines() if line.startswith("  - an option of an open list")
    )
    assert "`click X,Y` on it does nothing" in bullet
    assert "outside the page" in bullet
    assert "`key ArrowDown`" in bullet
    assert "`key Enter`" in bullet
    assert '`click "Druckschrift Nord"`' in bullet


def test_581_the_numbering_buttons_keep_their_spaces():
    # `click "123"` found nothing. The buttons under Nummerierung read `1 2 3` and `a b c`.
    how = section("## How the editor works")
    bullet = next(line for line in how.splitlines() if "Nummerierung" in line and "1 2 3" in line)
    assert '`click "1 2 3"`' in bullet
    assert "`a b c`" in bullet
    assert '`click "123"` finds nothing' in bullet
    numbering = (REPO / "frontend/src/components/Numbering.tsx").read_text()
    assert '"1 2 3"' in numbering
    assert '"a b c"' in numbering


def test_581_the_tick_grid_is_read_after_the_tool_picks_the_block():
    # The MCP snapshot lists no block, so the run could not pick one to read the grid's names.
    how = section("## How the editor works")
    bullet = next(
        line for line in how.splitlines() if line.startswith("- A block on the sheet has no name")
    )
    assert "snapshot does not list it" in bullet
    assert "`click X,Y`" in bullet
    assert "`Ausschnitt`" in bullet
    assert "`Selbst färben`" in bullet
    assert "`Selbst verdecken`" in bullet
    assert "`Feld 1`" in bullet and "`Feld 100`" in bullet
    assert "`Feld 0`" in bullet and "`Feld 99`" in bullet
    assert '`where "Feld 100"`' in bullet
    grid = (REPO / "frontend/src/pages/Hunderterfeld.tsx").read_text()
    assert "aria-label={`Feld ${v}`}" in grid
    source = frontend()
    for label in ("Ausschnitt", "Selbst färben", "Selbst verdecken", "0 bis 99"):
        assert on_screen(label, source), label
