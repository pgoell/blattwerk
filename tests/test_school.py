"""School tasks: times and divide with free digits, and a gap of two numbers."""

import pytest

from blattwerk.maths import Settings, generate


def blocks(count=12, seeds=20, **limits):
    """One block of `count` tasks for each seed."""
    return [
        generate(Settings(count=count, seed=seed, **limits))["exercises"] for seed in range(seeds)
    ]


def plain(e):
    """Whether a task has a 0 or a 1 as a factor, a divisor or a quotient."""
    return e["a"] in (0, 1) or e["b"] in (0, 1) or e["result"] in (0, 1)


@pytest.mark.parametrize("top", [10, 20, 100, 1000, 1_000_000])
def test_times_with_free_digits_sets_school_tasks(top):
    found = blocks(ops=["*"], max=top)
    if top == 10:
        # Only 8 school tasks fit in 10 and a block has 12: each block must hold all 8.
        school = {(a, b) for a in range(2, 11) for b in range(2, 11) if a * b <= 10}
        for block in found:
            assert {(e["a"], e["b"]) for e in block if e["a"] >= 2 and e["b"] >= 2} == school
        return
    tasks = [e for block in found for e in block]
    assert sum(plain(e) for e in tasks) <= 0.15 * len(tasks)
    if top >= 100:
        assert len({min(e["a"], e["b"]) for e in tasks}) >= 5


@pytest.mark.parametrize("top", [10, 20, 100, 1000, 1_000_000])
def test_divide_with_free_digits_sets_school_tasks(top):
    found = blocks(ops=["/"], max=top)
    if top == 10:
        # Only 8 school tasks fit in 10 and a block has 12: each block must hold all 8.
        school = {(a, b) for b in range(2, 11) for a in range(0, 11) if a % b == 0 and a // b >= 2}
        for block in found:
            assert {(e["a"], e["b"]) for e in block if e["b"] >= 2 and e["result"] >= 2} == school
        return
    tasks = [e for block in found for e in block]
    assert sum(e["b"] == 1 or e["result"] in (0, 1) for e in tasks) <= 0.15 * len(tasks)
    if top >= 100:
        assert len({e["b"] for e in tasks}) >= 5


@pytest.mark.parametrize(
    "top, ops, pvs, brackets, share",
    [
        (100, ["*"], False, False, 0.18),
        (1000, ["*"], False, False, 0.19),
        (100, ["*", "/"], False, False, 0.08),
        (1000, ["*", "/"], False, False, 0.08),
        (100, list("+-*/"), True, True, 0.21),
        (1000, list("+-*/"), True, True, 0.17),
    ],
)
def test_three_numbers_with_times_and_divide_set_school_tasks(top, ops, pvs, brackets, share):
    found = blocks(ops=ops, max=top, numbers=3, pvs=pvs, brackets=brackets)
    tasks = [e for block in found for e in block]
    assert sum(any(e[k] in (0, 1) for k in "abc") for e in tasks) <= share * len(tasks)


def test_a_gap_of_two_numbers_has_one_answer():
    for block in blocks(ops=["*", "/"], max=100, format="gap"):
        for e in block:
            a, b, result = e["a"], e["b"], e["result"]
            if (a, b) == (0, 0):
                continue
            if e["op"] == "*":
                by_a = [x for x in range(101) if x * b == result]
                by_b = [x for x in range(101) if a * x == result]
            else:
                by_a = [x for x in range(101) if x // b == result and x % b == 0]
                by_b = [x for x in range(1, 101) if a // x == result and a % x == 0]
            assert len(by_a if e["hide"] == "a" else by_b) == 1, e


def test_plus_and_minus_come_out_as_before():
    # Master's output before #441: the rng of "+" and "-" must be drawn as it was.
    row = generate(Settings(ops=["+", "-"], max=100, count=8, seed=5))["exercises"]
    assert [(e["op"], e["a"], e["b"], e["result"]) for e in row] == [
        ("-", 86, 73, 13),
        ("-", 63, 24, 39),
        ("-", 21, 6, 15),
        ("+", 23, 22, 45),
        ("+", 61, 11, 72),
        ("-", 28, 18, 10),
        ("+", 91, 6, 97),
        ("+", 34, 64, 98),
    ]
    gap = generate(Settings(ops=["+", "-"], max=100, count=6, seed=6, format="gap"))["exercises"]
    assert [(e["op"], e["a"], e["b"], e["result"], e["hide"]) for e in gap] == [
        ("+", 71, 14, 85, "a"),
        ("-", 2, 0, 2, "b"),
        ("+", 52, 47, 99, "b"),
        ("-", 64, 63, 1, "a"),
        ("-", 24, 1, 23, "a"),
        ("+", 6, 69, 75, "a"),
    ]
    three = generate(Settings(ops=["+", "-"], max=100, count=6, seed=7, numbers=3))["exercises"]
    assert [(e["a"], e["op"], e["b"], e["op2"], e["c"], e["result"]) for e in three] == [
        (50, "-", 41, "+", 6, 15),
        (46, "+", 37, "+", 1, 84),
        (11, "+", 55, "+", 26, 92),
        (11, "+", 70, "+", 13, 94),
        (28, "+", 7, "+", 50, 85),
        (5, "+", 71, "+", 4, 80),
    ]
    compare = generate(
        Settings(ops=["+", "-"], max=100, count=8, seed=8, format="compare", sides="tt")
    )["exercises"]

    def side(s):
        return (s["op"], s["a"], s["b"], s["value"])

    assert [(side(e["left"]), side(e["right"]), e["sign"]) for e in compare] == [
        (("-", 12, 1, 11), ("-", 79, 48, 31), "<"),
        (("+", 47, 24, 71), ("+", 24, 47, 71), "="),
        (("+", 51, 41, 92), ("+", 58, 31, 89), ">"),
        (("+", 84, 1, 85), ("-", 30, 22, 8), ">"),
        (("-", 29, 24, 5), ("+", 89, 4, 93), "<"),
        (("-", 60, 57, 3), ("-", 92, 14, 78), "<"),
        (("-", 49, 31, 18), ("+", 51, 5, 56), "<"),
        (("+", 10, 17, 27), ("+", 25, 2, 27), "="),
    ]
