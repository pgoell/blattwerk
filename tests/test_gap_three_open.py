"""Gap tasks of three numbers: a gap never hides a number that any number fits.

The fallback that hides a, b or c when no number is told by the result is the bug. The
result is hidden instead.
"""

import pytest

from blattwerk.maths import Settings, generate, told

ONE = [Settings(ops=["*"], max=1, format="gap", numbers=3, count=8, seed=s) for s in range(10)]
FIVE = [Settings(ops=["*"], max=5, format="gap", numbers=3, count=60, seed=s) for s in range(5)]


@pytest.mark.parametrize("s", [*ONE, *FIVE], ids=lambda s: f"max{s.max}-seed{s.seed}")
def test_a_gap_of_three_numbers_never_hides_a_number_that_any_number_fits(s):
    """H1: a gap of three numbers hides only a number that the result tells, or the result."""
    exercises = generate(s)["exercises"]
    for e in exercises:
        if "hide" in e:
            assert told(s, e, e["hide"]), e
    if s.max == 1:
        assert any("hide" not in e for e in exercises), "no exercise hides the result"


def test_a_gap_of_three_numbers_with_no_told_number_hides_the_result():
    """H1: a task with two zeros among its numbers hides the result, as no number is told."""
    for s in ONE:
        for e in generate(s)["exercises"]:
            zeros = [e[k] for k in "abc"].count(0)
            if zeros >= 2:
                assert "hide" not in e, e
