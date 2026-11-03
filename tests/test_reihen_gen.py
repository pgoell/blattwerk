"""Einmaleins-Reihen on a maths block, and Geteilt mit Rest (issue #840).

A teacher picks any of the rows 1 to 10. Kernaufgaben are the rows 1, 2, 5 and 10.
The rows apply to Mal and Geteilt. With a remainder, "Rest 0 vermeiden" keeps a
remainder of 0 out, and the Rest can be the only Lücke.
"""

from blattwerk.maths import Settings, generate
from blattwerk.maths.pairs import valid


def test_times_tasks_stay_in_the_chosen_rows():
    """Mal with the 3er and 4er Reihe: one factor is 3 or 4, and both are from 1 to 10."""
    out = generate(Settings(ops=["*"], max=100, count=12, seed=3, reihen=[3, 4]))
    assert len(out["exercises"]) == 12
    assert out["loosen"] is None
    for e in out["exercises"]:
        assert e["a"] in (3, 4) or e["b"] in (3, 4)
        assert 1 <= e["a"] <= 10 and 1 <= e["b"] <= 10


def test_divide_tasks_use_the_chosen_divisor():
    """Geteilt with the 6er Reihe: the divisor is 6 and the quotient is from 1 to 10."""
    out = generate(Settings(ops=["/"], max=100, count=10, seed=5, reihen=[6]))
    assert len(out["exercises"]) == 10
    for e in out["exercises"]:
        assert e["b"] == 6
        assert 1 <= e["result"] <= 10
        assert e["result"] * e["b"] + e["rest"] == e["a"]


def test_kernaufgaben_keep_to_the_rows_1_2_5_and_10():
    """The Kernaufgaben preset is the rows 1, 2, 5 and 10, also in a large Zahlenraum."""
    out = generate(Settings(ops=["*"], max=1_000_000, count=20, seed=8, reihen=[1, 2, 5, 10]))
    assert len(out["exercises"]) == 20
    for e in out["exercises"]:
        assert e["a"] in (1, 2, 5, 10) or e["b"] in (1, 2, 5, 10)
        assert 1 <= e["a"] <= 10 and 1 <= e["b"] <= 10


def test_too_few_tasks_name_the_rows():
    """One row and no 1 cannot fill 100 tasks, and the line names the rows."""
    out = generate(Settings(ops=["*"], max=100, count=100, seed=1, reihen=[7], one=False))
    assert len(out["exercises"]) < 100
    assert "reihen" in out["loosen"]


def test_an_empty_row_list_draws_the_same_tasks():
    """No rows chosen leaves the tasks as they are without the field."""
    plain = generate(Settings(ops=["*"], max=100, count=8, seed=2))
    empty = generate(Settings(ops=["*"], max=100, count=8, seed=2, reihen=[]))
    assert empty == plain


def test_three_numbers_ignore_the_rows():
    """Three numbers draw the same tasks whether or not rows are chosen."""

    def make(reihen):
        return generate(
            Settings(ops=["*"], max=100, count=4, seed=1, numbers=3, format="row", reihen=reihen)
        )

    assert make([3]) == make([])


def test_comparisons_keep_the_chosen_row():
    """A comparison of times terms stays in the chosen row."""
    out = generate(
        Settings(ops=["*"], max=100, format="compare", sides="tt", count=6, seed=2, reihen=[5])
    )
    assert len(out["exercises"]) == 6
    for e in out["exercises"]:
        for side in (e["left"], e["right"]):
            assert side["a"] == 5 or side["b"] == 5
            assert 1 <= side["a"] <= 10 and 1 <= side["b"] <= 10


def test_a_rest_of_zero_stays_out_when_the_teacher_avoids_it():
    """Rest 0 vermeiden: 12 : 4 is no task, and no drawn task has a remainder of 0."""
    kept = Settings(ops=["/"], max=40, count=1, seed=1, rest=True, avoid0=True)
    assert not valid(kept, "/", 12, 4, 40)
    out = generate(Settings(ops=["/"], max=40, count=15, seed=2, rest=True, avoid0=True))
    assert out["exercises"]
    assert all(e["rest"] > 0 for e in out["exercises"])


def test_a_rest_of_zero_stands_when_the_teacher_allows_it():
    """With Rest 0 vermeiden off, an even division may stand among the tasks with a rest."""
    allowed = Settings(ops=["/"], max=40, count=1, seed=1, rest=True, avoid0=False)
    assert valid(allowed, "/", 12, 4, 40)
    out = generate(
        Settings(ops=["/"], max=20, count=30, seed=1, rest=True, avoid0=False, b=[(2, 4)])
    )
    assert any(e["rest"] == 0 for e in out["exercises"])
    assert any(e["rest"] > 0 for e in out["exercises"])


def test_the_rest_can_be_the_only_gap():
    """A Lücke on the Rest alone hides no other number, and the remainder stays."""
    out = generate(
        Settings(ops=["/"], max=30, count=8, seed=4, rest=True, format="gap", gaps=["rest"])
    )
    assert len(out["exercises"]) == 8
    assert all(e.get("hide") == "rest" and e["rest"] > 0 for e in out["exercises"])


def test_the_rest_gap_can_stand_beside_the_result():
    """Ticked Rest and Ergebnis: the gap hides the quotient, and there is a remainder."""
    out = generate(
        Settings(
            ops=["/"],
            max=30,
            count=6,
            seed=6,
            rest=True,
            format="gap",
            gaps=["result", "rest"],
        )
    )
    assert out["exercises"]
    assert all(e.get("hide", "result") == "result" and e["rest"] > 0 for e in out["exercises"])
