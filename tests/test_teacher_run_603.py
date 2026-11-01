"""What issue #603 found in the brief's twelfth run, where it is still open."""

from test_teacher_run import on_screen, section
from test_teacher_run_issues import frontend

from blattwerk.templates import BUILT_IN


def seeded(template):
    """Block types on this template that carry a seed, so a second start draws new tasks."""
    return [
        block["type"]
        for page in template["doc"]["pages"]
        for block in page["blocks"]
        if "seed" in block["props"]
    ]


def test_603_only_the_four_rechenblaetter_are_started_twice():
    # The run started each template twice. Only the four Rechenblätter draw new tasks.
    intro = section("### 5. ")
    assert "Only the four Rechenblätter draw new tasks" in intro
    for n in range(1, 5):
        assert f"`Rechenblatt Klasse {n}`" in intro
    assert "start from those four twice" in intro
    assert "every other built-in template once" in intro
    assert "`Schreibblatt Lineatur 1` is the same both times" in intro
    names = [template["name"] for template in BUILT_IN if seeded(template)]
    assert names == [f"Rechenblatt Klasse {n}" for n in range(1, 5)]
    schreib = next(
        template for template in BUILT_IN if template["name"] == "Schreibblatt Lineatur 1"
    )
    assert seeded(schreib) == []


def test_603_change_the_tasks_is_neu_wuerfeln_and_is_not_skipped():
    # "Change the tasks" on a template sheet was skipped for time. The button is one click.
    intro = section("### 5. ")
    assert "click `Neu würfeln`" in intro
    assert "That is one click, so it is not skipped for time." in intro
    assert on_screen("Neu würfeln", frontend())


def test_603_a_greyed_control_outside_the_window_still_says_so():
    rules = section("## Rules")
    assert "also after the tool turned the panel to one that lay outside the window" in rules
