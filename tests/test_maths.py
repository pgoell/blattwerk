import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from playwright.sync_api import expect
from pydantic import ValidationError
from ui import at, box, expect_picked, maths, pick, saved, user

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
compares = st.builds(
    Settings,
    ops=st.lists(st.sampled_from("+-*/"), min_size=1, max_size=4),
    max=st.sampled_from([10, 20, 100, 1000, 1_000_000]) | st.integers(1, 1_000_000),
    a=places,
    b=places,
    carry=st.sampled_from(["none", "required", "either"]),
    rest=st.booleans(),
    format=st.just("compare"),
    sides=st.sampled_from(["nn", "tn", "tt"]),
    close=st.booleans(),
    equal=st.sampled_from(["none", "some"]),
    count=st.integers(1, 30),
    seed=st.integers(0, 10**9),
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
        for x1, x2, above, kind in grid["lines"]:
            if above == y and kind in kinds:
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
    for bad in (
        {"max": 0},
        {"max": 10**7},
        {"count": 0},
        {"ops": []},
        {"a": [(5, 4)]},
        {"sides": "x"},
        {"equal": "all"},
    ):
        with pytest.raises(ValidationError):
            settings_for(**bad)


@given(compares)
# Each example runs the generator's full try budget several times, so 300 would near the 60 s limit.
@settings(max_examples=100, deadline=None)
def test_every_comparison_keeps_every_limit(s):
    out = generate(s)
    exercises = out["exercises"]
    plain = s.model_copy(update={"rest": False})
    shape = {"nn": ["num", "num"], "tn": ["term", "num"], "tt": ["term", "term"]}[s.sides]
    for e in exercises:
        assert set(e) == {"left", "right", "sign"}
        for side, kind in zip((e["left"], e["right"]), shape, strict=True):
            if kind == "term":
                assert set(side) == {"op", "a", "b", "value"}
                e_term = {**side, "result": side["value"], "rest": 0}
                assert keeps(plain, e_term)
                assert side["op"] != "/" or side["a"] % side["b"] == 0
            else:
                assert set(side) == {"value"} and 0 <= side["value"] <= s.max
        left, right = e["left"]["value"], e["right"]["value"]
        assert e["sign"] == ("=" if left == right else "<" if left < right else ">")
        if s.close and e["sign"] != "=":
            assert abs(left - right) in {1, 2, 10, 20}
    if s.sides == "nn":
        assert all(
            in_places(e["left"]["value"], s.a) and in_places(e["right"]["value"], s.b)
            for e in exercises
        )
    equal_tasks = sum(e["sign"] == "=" for e in exercises)
    assert (equal_tasks == 0) if s.equal == "none" else (equal_tasks <= (2 * s.count + 5) // 10)
    assert len({repr(e) for e in exercises}) == len(exercises) <= s.count
    assert (out["loosen"] is None) == (len(exercises) == s.count)
    assert generate(s) == out


@pytest.mark.parametrize("sides", ["nn", "tn", "tt"])
@pytest.mark.parametrize("close", [False, True])
@pytest.mark.parametrize("top", [20, 100, 1000])
def test_comparisons_in_a_plain_zahlenraum_are_all_there(sides, close, top):
    s = settings_for(
        format="compare", sides=sides, close=close, ops=["+", "-"], max=top, count=10, equal="some"
    )
    out = generate(s)
    assert len(out["exercises"]) == 10 and out["loosen"] is None
    assert sum(e["sign"] == "=" for e in out["exercises"]) == 2
    none = generate(s.model_copy(update={"equal": "none"}))
    assert len(none["exercises"]) == 10 and none["loosen"] is None
    assert all(e["sign"] != "=" for e in none["exercises"])


def test_comparisons_of_products_and_quotients_in_a_plain_zahlenraum_are_all_there():
    s = settings_for(format="compare", sides="tt", close=True, ops=["*", "/"], max=100, count=10)
    assert len(generate(s)["exercises"]) == 10


@pytest.mark.parametrize(
    "count, equal_tasks", [(1, 0), (2, 0), (3, 1), (7, 1), (8, 2), (12, 2), (20, 4)]
)
def test_the_share_of_equal_tasks(count, equal_tasks):
    s = settings_for(format="compare", sides="tn", ops=["+", "-"], max=100, count=count)
    assert sum(e["sign"] == "=" for e in generate(s)["exercises"]) == equal_tasks


def test_a_seed_brings_the_same_comparisons_and_another_seed_others():
    big = settings_for(format="compare", sides="tt", ops=["+", "-", "*", "/"], max=1000, count=40)
    assert generate(big) == generate(big)
    assert generate(big) != generate(big.model_copy(update={"seed": 2}))


def test_names_what_stands_in_the_way_of_a_comparison():
    # Only 1 stands on the left and only 5 on the right, so 1 = 5 is never there.
    ones = dict(format="compare", sides="nn", a=[(1, 1), (0, 0)], b=[(5, 5), (0, 0)], max=10)
    out = generate(settings_for(**ones, count=5, equal="some"))
    assert [e["sign"] for e in out["exercises"]] == ["<"]
    assert out["loosen"] == ["a", "b"]
    # With 2 to 9 on the right, 1 = 2 to 9 is out, but 1 < 2 to 9 gives 4 tasks without it.
    twos = dict(ones, b=[(2, 9), (0, 0)])
    out = generate(settings_for(**twos, count=5, equal="some"))
    assert len(out["exercises"]) == 4 and "equal" in out["loosen"]
    out = generate(settings_for(**ones, count=5, close=True, equal="none"))
    assert out["exercises"] == [] and {"close", "a", "b"} <= set(out["loosen"])
    # In a Zahlenraum of 3 there are too few comparisons for 100; a higher top gives terms room.
    few = generate(settings_for(format="compare", sides="tn", max=3, count=100, equal="none"))
    assert len(few["exercises"]) < 100 and "max" in few["loosen"]


def test_a_division_in_a_comparison_comes_out_even():
    s = settings_for(format="compare", ops=["/"], rest=True, sides="tt", max=100, count=10)
    exercises = generate(s)["exercises"]
    assert exercises
    for e in exercises:
        for side in (e["left"], e["right"]):
            assert side["a"] % side["b"] == 0


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
        assert e.get("hide") in ("a", "b", "c") if s.format == "gap" else e.get("hide") is None
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


@pytest.mark.parametrize("carry", ["none", "required", "either"])
@pytest.mark.parametrize("top", [10, 20, 100, 1000])
def test_a_chain_of_plus_and_minus_fills_a_block(top, carry):
    out = generate(settings_for(ops=["+", "-"], max=top, count=12, numbers=3, carry=carry))
    if len(out["exercises"]) < 12:
        assert out["loosen"]
    else:
        assert out["loosen"] is None


def test_a_seed_brings_the_same_tasks_of_three_and_another_seed_others():
    big = settings_for(ops=list("+-*/"), max=1000, count=40, numbers=3, pvs=True, brackets=True)
    assert generate(big) == generate(big)
    assert generate(big) != generate(big.model_copy(update={"seed": 2}))


def test_two_numbers_come_out_as_before():
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


def test_names_the_third_number_as_the_limit_in_the_way():
    # Only a units digit of 7 is allowed for the third number, and the carries leave 10 tasks.
    out = generate(
        settings_for(ops=["+", "-"], max=10, count=20, numbers=3, c=[(7, 7)], carry="required")
    )
    assert len(out["exercises"]) == 10
    assert "c" in out["loosen"]


def bare(client):
    """A maths block's props as a sheet saved through the API may hold them: no digit ranges."""
    props = maths(client)
    del props["a"], props["b"]
    return props


def test_a_block_with_no_digit_ranges_stays_when_it_is_clicked(editor):
    client = user()
    page = editor(box("m", "maths", bare(client)), client=client)
    at(page, "m").click()
    expect(at(page, "m")).to_be_visible()
    expect_picked(page, "m")
    expect(page.locator(".panel").get_by_label("Zahlenraum")).to_have_value("20")


def test_a_block_with_no_digit_ranges_takes_any_digit_and_rolls_anew(editor):
    client = user()
    page = editor(box("m", "maths", bare(client)), client=client)
    pick(page, "m")
    # Bis 20: Einer and Zehner for each of the two numbers, any digit in each.
    panel = page.locator(".panel")
    for place in ("E", "Z"):
        expect(panel.get_by_label(f"{place} von")).to_have_count(2)
        for who in (0, 1):
            expect(panel.get_by_label(f"{place} von").nth(who)).to_have_value("0")
            expect(panel.get_by_label(f"{place} bis").nth(who)).to_have_value("9")
    expect(panel.get_by_label("H von")).to_have_count(0)
    panel.get_by_role("button", name="Neu würfeln").click()
    expect(page.locator("header [role=status]")).to_have_text("Speichert …")
    expect(at(page, "m").locator(".maths > div")).to_have_count(3)
    props = saved(page, client)[0]["props"]
    assert props["a"] == props["b"] == [[0, 9], [0, 9]]
    assert props["seed"] != 7 and len(props["exercises"]) == 3
