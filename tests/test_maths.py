import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from blattwerk.maths import ANSWER, CARRY, Settings, below, generate, nth, written

place = st.tuples(st.integers(0, 9), st.integers(0, 9)).map(sorted).map(tuple)
places = st.lists(place, max_size=7)
limits = st.builds(
    Settings,
    ops=st.lists(st.sampled_from("+-*/"), min_size=1, max_size=4),
    max=st.sampled_from([10, 20, 100, 1000, 1_000_000]) | st.integers(1, 1_000_000),
    a=places,
    b=places,
    carry=st.sampled_from(["none", "required", "either"]),
    rest=st.booleans(),
    format=st.sampled_from(["row", "gap", "written"]),
    count=st.integers(1, 30),
    seed=st.integers(0, 10**9),
)


def digit_sum(n):
    return sum(map(int, str(n)))


def in_places(n, ranges):
    return all(lo <= n // 10**i % 10 <= hi for i, (lo, hi) in enumerate(ranges))


def keeps(s, e, top=None):
    """Whether one exercise keeps every limit, worked out apart from the generator."""
    a, b, op = e["a"], e["b"], e["op"]
    ok = op in s.ops and 0 <= a <= s.max and 0 <= b <= s.max
    ok = ok and in_places(a, s.a) and in_places(b, s.b) and 0 <= e["result"] <= (top or s.max)
    if op in "+-":
        # Each carry takes ten from one place and gives one to the next: nine less in the digits.
        big, parts = (a + b, [a, b]) if op == "+" else (a, [a - b, b])
        carried = sum(map(digit_sum, parts)) > digit_sum(big)
        ok = ok and e["result"] == (a + b if op == "+" else a - b) and e["rest"] == 0
        return ok and (s.carry == "either" or carried == (s.carry == "required"))
    if op == "*":
        return ok and e["result"] == a * b and e["rest"] == 0
    return ok and b > 0 and e["result"] * b + e["rest"] == a and 0 <= e["rest"] < b


def text(grid, kinds=(0, 1, 2)):
    """A written exercise as lines of text: dashes for a ruled line, a tilde for a minus sign."""
    rows = [[" "] * grid["cols"] for _ in range(grid["rows"])]
    for x, y, ch, kind in grid["cells"]:
        assert rows[y][x] == " ", "two characters in one cell"
        if kind in kinds:
            rows[y][x] = ch
    out = []
    for y, row in enumerate(rows):
        for x1, x2, at, kind in grid["lines"]:
            if at == y and kind in kinds:
                out.append((" " * x1 + "-" * (x2 - x1)).rstrip())
        out.append("".join(row).rstrip())
    return "\n".join(out).replace("\u2212", "~")


@given(limits)
@settings(max_examples=300, deadline=None)
def test_every_exercise_keeps_every_limit(s):
    out = generate(s)
    exercises = out["exercises"]
    assert all(keeps(s, e) for e in exercises)
    assert all(e["rest"] > 0 if s.rest else e["rest"] == 0 for e in exercises if e["op"] == "/")
    # No exercise twice, and never more than asked for.
    assert len({(e["op"], e["a"], e["b"]) for e in exercises}) == len(exercises) <= s.count
    assert (out["loosen"] is None) == (len(exercises) == s.count)
    assert generate(s) == out
    for e in exercises:
        assert e.get("hide") in (("a", "b") if s.format == "gap" else (None,))
        assert ("grid" in e) == (s.format == "written")


@given(limits.filter(lambda s: s.max <= 30 or random.Random(s.seed).random() < 0.1))
@settings(max_examples=150, deadline=None)
def test_no_exercise_is_missed_in_a_small_zahlenraum(s):
    """Where every pair of numbers can be tried, the generator finds as many as there are."""
    if (s.max + 1) ** 2 > 20_000:
        s = s.model_copy(update={"max": 30, "a": s.a[:2], "b": s.b[:2]})
    ops = list(dict.fromkeys(s.ops))
    out = generate(s)
    for i, op in enumerate(ops):
        every = 0
        for a in range(s.max + 1):
            for b in range(s.max + 1):
                if (op == "/" and (b == 0 or (a % b > 0) != s.rest)) or (op == "-" and a < b):
                    continue
                result = {"+": a + b, "-": a - b, "*": a * b}.get(op) if op != "/" else a // b
                e = {"op": op, "a": a, "b": b, "result": result, "rest": a % b if op == "/" else 0}
                every += keeps(s, e)
        share = s.count // len(ops) + (i < s.count % len(ops))
        assert sum(e["op"] == op for e in out["exercises"]) == min(share, every)


@given(st.lists(place, min_size=1, max_size=7), st.integers(0, 10**7))
def test_numbers_with_such_digits_count_up_in_order(ranges, bound):
    n = below(ranges, bound)
    assert n == below(ranges, 10**7) or nth(ranges, n) > bound
    assert n == 0 or nth(ranges, n - 1) <= bound
    assert n < 2 or nth(ranges, n - 2) < nth(ranges, n - 1)
    assert in_places(nth(ranges, max(0, n - 1)), ranges)


@given(st.sampled_from("+-*/"), st.integers(0, 10**6), st.integers(1, 10**6))
def test_written_answer_is_the_result(op, a, b):
    if op == "-" and a < b:
        a, b = b, a
    grid = written(op, a, b)
    assert all(0 <= x < grid["cols"] and 0 <= y < grid["rows"] for x, y, _, _ in grid["cells"])
    assert all(
        0 <= x1 < x2 <= grid["cols"] and 0 < y < grid["rows"] for x1, x2, y, _ in grid["lines"]
    )
    task, answer = text(grid, [0]).split("\n"), text(grid, [ANSWER]).split("\n")
    sign = {"+": "+", "-": "~", "*": "·", "/": ":"}[op]
    if op == "/":
        rest = f"R{a % b}" if a % b else ""
        assert task[0].strip() == f"{a}{sign}{b}="
        assert answer[0].strip() == f"{a // b}{rest}"
        assert int(answer[-1]) == a % b
    elif op == "*":
        assert task[0].strip() == f"{a}{sign}{b}"
        assert int(answer[-1]) == a * b
    else:
        assert [task[0].strip(), task[1].replace(" ", "")] == [str(a), f"{sign}{b}"]
        assert int(answer[-1]) == (a + b if op == "+" else a - b)


def test_written_methods():
    assert text(written("+", 478, 256)) == " 478\n+256\n 11\n----\n 734"
    assert text(written("-", 503, 78)) == " 503\n~ 78\n 11\n----\n 425"
    assert text(written("*", 234, 6)) == "234·6\n-----\n 1404"
    assert text(written("*", 234, 56)) == "234·56\n------\n 1170\n  1404\n  1\n------\n 13104"
    assert text(written("/", 936, 4)) == (
        " 936:4=234\n~8\n -\n 13\n~12\n --\n  16\n ~16\n  --\n   0"
    )
    assert text(written("/", 7, 9)) == " 7:9=0R7\n~0\n -\n 7"
    assert text(written("/", 1005, 25)) == " 1005:25=40R5\n~100\n ---\n   05\n   ~0\n   --\n    5"
    # The sheet shows the exercise alone; the working and the carries are the answer key's.
    assert text(written("/", 936, 4), [0]).strip() == "936:4="
    assert text(written("+", 478, 256), [CARRY]).strip() == "11"


def settings_for(**limits):
    return Settings.model_validate({"ops": ["+"], "max": 100, "count": 5, "seed": 1, **limits})


def test_names_the_limit_to_loosen():
    high = [(5, 9), (0, 9), (0, 9)]
    out = generate(settings_for(a=high, b=high, carry="none"))
    assert out == {"exercises": [], "loosen": ["carry", "a", "b"]}
    out = generate(settings_for(a=[(0, 9), (6, 9)], b=[(0, 9), (6, 9)]))
    assert out == {"exercises": [], "loosen": ["a", "b", "max"]}
    assert generate(settings_for(ops=["/"], b=[(1, 1), (0, 0)], rest=True))["loosen"] == [
        "rest",
        "b",
    ]
    seven = generate(settings_for(ops=["/"], max=1_000_000, a=[(7, 7)] + [(0, 0)] * 6, count=9))
    assert [e["b"] for e in seven["exercises"]] == [7] or seven["loosen"]
    # Only so many exercises exist: 0 + 0 up to 10 + 0.
    out = generate(settings_for(max=10, count=100))
    assert len(out["exercises"]) == 66
    assert out["loosen"] == ["max"]


def test_a_seed_brings_the_same_exercises_and_another_seed_others():
    big = settings_for(ops=["+", "-", "*", "/"], max=1_000_000, count=40)
    assert generate(big) == generate(big)
    assert generate(big) != generate(big.model_copy(update={"seed": 2}))
    assert {e["op"] for e in generate(big)["exercises"]} == set("+-*/")


def test_turns_down_limits_that_make_no_sense():
    for bad in ({"max": 0}, {"max": 10**7}, {"count": 0}, {"ops": []}, {"a": [(5, 4)]}):
        with pytest.raises(ValidationError):
            settings_for(**bad)
