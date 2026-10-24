"""Tasks of three numbers: the result, the gap, and what a block fills with.

The helpers live in test_maths.py.
"""

from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from test_maths import (
    digit_sum,
    in_places,
    places,
    settings_for,
)

from blattwerk.maths import (
    Settings,
    generate,
)

threes = st.builds(
    Settings,
    ops=st.lists(st.sampled_from("+-*/"), min_size=1, max_size=4),
    max=st.sampled_from([10, 20, 100, 1000, 1_000_000]) | st.integers(1, 1_000_000),
    a=places,
    b=places,
    c=places,
    carry=st.sampled_from(["none", "required", "either"]),
    numbers=st.just(3),
    pvs=st.booleans(),
    brackets=st.booleans(),
    format=st.sampled_from(["row", "gap"]),
    count=st.integers(1, 30),
    seed=st.integers(0, 10**9),
)


def apply(op, x, y):
    """One step with Python's own arithmetic; a division by nothing is NaN, so it fails a check."""
    return {"+": x + y, "-": x - y, "*": x * y, "/": x / y if y else float("nan")}[op]


def steps_of(e):
    """The two steps of a three-number exercise, read from its brackets and the kinds of its ops."""
    a, b, c, o1, o2 = e["a"], e["b"], e["c"], e["op"], e["op2"]
    if e.get("paren") == "right" or (e.get("paren") is None and o1 in "+-" and o2 in "*/"):
        inner = (o2, b, c)
        return [inner, (o1, a, apply(*inner))]
    inner = (o1, a, b)
    return [inner, (o2, apply(*inner), c)]


def carried(op, x, y):
    """Whether a sum or a difference carries or borrows: each one costs nine in the digit sums."""
    x, y = int(x), int(y)
    if op == "+":
        return digit_sum(x) + digit_sum(y) > digit_sum(x + y)
    return digit_sum(x - y) + digit_sum(y) > digit_sum(x)


@given(threes)
@settings(max_examples=300, deadline=None)
def test_every_task_of_three_numbers_keeps_every_limit_and_its_result_is_right(s):
    out = generate(s)
    exercises = out["exercises"]
    rule = s.pvs and any(o in "+-" for o in s.ops) and any(o in "*/" for o in s.ops)
    for e in exercises:
        a, b, c, o1, o2, paren = e["a"], e["b"], e["c"], e["op"], e["op2"], e.get("paren")
        for op, x, y in steps_of(e):
            value = apply(op, x, y)
            if op == "/":
                assert y > 0 and x % y == 0
            assert 0 <= value <= s.max
            if op in "+-" and s.carry != "either":
                assert carried(op, x, y) == (s.carry == "required")
        shown = (
            f"({a} {o1} {b}) {o2} {c}"
            if paren == "left"
            else f"{a} {o1} ({b} {o2} {c})"
            if paren == "right"
            else f"{a} {o1} {b} {o2} {c}"
        )
        assert eval(shown) == e["result"] and e["rest"] == 0
        assert o1 in s.ops and o2 in s.ops
        assert in_places(a, s.a) and in_places(b, s.b) and in_places(c, s.c)
        assert max(a, b, c) <= s.max
        # No hide in a gap task is the result hidden: where no number is told by it (0 · 0 · 1).
        assert e.get("hide") in ("a", "b", "c", None) if s.format == "gap" else "hide" not in e
        assert paren in (None, "left", "right")
        if rule:
            assert (o1 in "+-") != (o2 in "+-")
            assert paren != "left" or o1 in "+-"
            assert paren != "right" or o2 in "+-"
        else:
            assert (o1 in "+-") == (o2 in "+-") and paren is None
        assert paren is None or (rule and s.brackets)
    keys = [(e["a"], e["op"], e["b"], e["op2"], e["c"], e.get("paren")) for e in exercises]
    assert len(set(keys)) == len(keys) <= s.count
    assert (out["loosen"] is None) == (len(exercises) == s.count)
    assert generate(s) == out


def test_punkt_stands_first_in_half_of_the_tasks_and_brackets_in_half():
    s = settings_for(ops=list("+-*/"), max=100, count=20, numbers=3, pvs=True)
    exercises = generate(s)["exercises"]
    assert len(exercises) == 20
    assert sum(e["op"] in "*/" for e in exercises) == 10
    with_brackets = generate(s.model_copy(update={"brackets": True}))["exercises"]
    assert len(with_brackets) == 20
    assert sum("paren" in e for e in with_brackets) == 10
    # Still 10 with brackets: two shapes start with the Punkt op, one plain and one bracketed.
    assert sum(e["op"] in "*/" for e in with_brackets) == 10
    # Plain and bracketed tasks alternate, so even a short block has some brackets.
    few = s.model_copy(update={"brackets": True})
    assert (
        sum("paren" in e for e in generate(few.model_copy(update={"count": 2}))["exercises"]) == 1
    )
    assert sum(
        "paren" in e for e in generate(few.model_copy(update={"count": 3}))["exercises"]
    ) in (1, 2)


@pytest.mark.parametrize("carry", ["none", "required", "either"])
@pytest.mark.parametrize("top", [10, 20, 100, 1000, 100_000, 1_000_000])
def test_a_chain_of_plus_and_minus_fills_a_block(top, carry):
    out = generate(settings_for(ops=["+", "-"], max=top, count=12, numbers=3, carry=carry))
    if len(out["exercises"]) < 12:
        assert out["loosen"]
    else:
        assert out["loosen"] is None


@pytest.mark.parametrize("top", [100_000, 1_000_000])
@pytest.mark.parametrize(
    "ops, pvs, brackets",
    [
        (["+"], False, False),
        (["-"], False, False),
        (["+", "-"], False, False),
        (["+", "-", "*", "/"], True, False),
        (["+", "-", "*", "/"], True, True),
    ],
)
@pytest.mark.parametrize("seed", range(1, 6))
def test_ohne_uebertrag_fills_a_block_in_a_big_zahlenraum(top, ops, pvs, brackets, seed):
    s = settings_for(
        ops=ops, max=top, count=12, numbers=3, carry="none", pvs=pvs, brackets=brackets, seed=seed
    )
    out = generate(s)
    assert len(out["exercises"]) == 12
    assert out["loosen"] is None


def test_a_seed_brings_the_same_tasks_of_three_and_another_seed_others():
    big = settings_for(ops=list("+-*/"), max=1000, count=40, numbers=3, pvs=True, brackets=True)
    assert generate(big) == generate(big)
    assert generate(big) != generate(big.model_copy(update={"seed": 2}))


def test_two_numbers_come_out_as_before():
    # Master's output from before three numbers came, with and without the new fields.
    pins = [
        (
            dict(ops=["+", "-"], max=20, count=4, seed=7),
            [
                ("+", 1, 17, 18, None),
                ("-", 13, 10, 3, None),
                ("-", 17, 13, 4, None),
                ("+", 4, 4, 8, None),
            ],
        ),
        # The times and divide pin is from after #441.
        (
            dict(ops=["*", "/"], max=100, count=4, seed=11, format="gap", rest=False),
            [
                ("*", 11, 6, 66, "b"),
                ("/", 100, 10, 10, "b"),
                ("*", 9, 2, 18, "b"),
                ("/", 85, 5, 17, "a"),
            ],
        ),
        (
            dict(ops=["+"], max=1000, count=3, seed=3, carry="required"),
            [("+", 557, 66, 623, None), ("+", 378, 618, 996, None), ("+", 485, 67, 552, None)],
        ),
    ]
    for base, want in pins:
        for extra in ({}, dict(numbers=2, pvs=True, brackets=True, c=[(1, 2)])):
            s = Settings.model_validate({**base, **extra})
            got = [
                (e["op"], e["a"], e["b"], e["result"], e.get("hide"))
                for e in generate(s)["exercises"]
            ]
            assert got == want
    extra = dict(numbers=2, pvs=True, brackets=True, c=[(1, 2)])
    for base in (
        dict(ops=list("+-*/"), max=100, count=20, seed=3),
        dict(ops=["-", "/"], max=1000, count=15, seed=4, format="gap", carry="required"),
    ):
        assert generate(Settings.model_validate({**base, **extra})) == generate(
            Settings.model_validate(base)
        )
    for fmt in ("written", "compare"):
        base = dict(ops=list("+-*/"), max=100, count=10, seed=5, format=fmt)
        threes_too = dict(numbers=3, pvs=True, brackets=True, c=[(1, 2)])
        assert generate(Settings.model_validate({**base, **threes_too})) == generate(
            Settings.model_validate(base)
        )


def fits_at(e, k, x):
    """Whether the task comes out at its result when the hidden number k is x, worked exactly."""
    nums = {j: Fraction(e[j]) for j in "abc"}
    nums[k] = Fraction(x)
    return apply(*steps_of({**e, **nums})[1]) == e["result"]


@pytest.mark.parametrize("ops", [["*"], ["*", "/"], ["+", "-", "*", "/"]])
def test_a_gap_of_three_numbers_has_one_answer(ops):
    unclear = total = 0
    for seed in range(20):
        s = Settings(
            ops=ops, max=100, count=12, numbers=3, pvs=True, brackets=True, format="gap", seed=seed
        )
        for e in generate(s)["exercises"]:
            total += 1
            # Only a number the result tells can be the gap; a task where none is told is no fault.
            told = {k: sum(fits_at(e, k, x) for x in range(101)) == 1 for k in "abc"}
            if not any(told.values()):
                unclear += 1
                continue
            assert told[e["hide"]]
    assert unclear * 10 < total


def test_names_the_third_number_as_the_limit_in_the_way():
    # Only a units digit of 7 is allowed for the third number, and the carries leave 10 tasks.
    out = generate(
        settings_for(ops=["+", "-"], max=10, count=20, numbers=3, c=[(7, 7)], carry="required")
    )
    assert len(out["exercises"]) == 10
    assert "c" in out["loosen"]
