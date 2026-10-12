import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from blattwerk.maths import ANSWER, CARRY, Settings, generate, places, written

place = st.tuples(st.integers(0, 9), st.integers(0, 9)).map(sorted).map(tuple)
places_of_digits = st.lists(place, max_size=7)
decimal_limits = st.builds(
    Settings,
    ops=st.lists(st.sampled_from("+-"), min_size=1, max_size=2, unique=True),
    max=st.sampled_from([10, 20, 100, 1000, 1_000_000]),
    decimals=st.sampled_from([0, 1, 2]),
    money=st.booleans(),
    af=st.lists(place, max_size=2),
    bf=st.lists(place, max_size=2),
    cf=st.lists(place, max_size=2),
    a=places_of_digits,
    b=places_of_digits,
    c=places_of_digits,
    carry=st.sampled_from(["none", "required", "either"]),
    format=st.sampled_from(["row", "gap", "written"]),
    numbers=st.sampled_from([2, 3]),
    count=st.integers(1, 12),
    seed=st.integers(0, 10**9),
)


def in_places(n, ranges):
    return all(lo <= n // 10**i % 10 <= hi for i, (lo, hi) in enumerate(ranges))


def carried(op, a, b):
    """Whether a sum or a difference carries or borrows in any place, worked digit by digit."""
    c, out = 0, False
    while a or b:
        c = a % 10 + b % 10 + c > 9 if op == "+" else a % 10 - c < b % 10
        out = out or bool(c)
        a, b = a // 10, b // 10
    return out


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
    return "\n".join(out).replace("\N{MINUS SIGN}", "~")


def walk(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)
    else:
        yield x


@given(decimal_limits)
@settings(max_examples=50, deadline=None)
def test_every_decimal_task_keeps_every_limit_and_its_result_is_right(s):
    d = places(s)
    top = s.max * 10**d
    ranges = {
        "a": [*reversed(s.af[:d]), *s.a],
        "b": [*reversed(s.bf[:d]), *s.b],
        "c": [*reversed(s.cf[:d]), *s.c],
    }

    def step(op, x, y):
        """One step worked out here: its result, and whether its carry keeps the setting."""
        r = x + y if op == "+" else x - y
        assert 0 <= r <= top
        if s.carry != "either":
            assert (s.carry == "required") == carried(op, x, y)
        return r

    for e in generate(s)["exercises"]:
        names = "abc" if "op2" in e else "ab"
        for k in names:
            assert type(e[k]) is int and 0 <= e[k] <= top
            assert in_places(e[k], ranges[k])
        assert type(e["result"]) is int
        if "op2" in e:
            v = step(e["op"], e["a"], e["b"])
            assert e["result"] == step(e["op2"], v, e["c"])
        else:
            assert e["result"] == step(e["op"], e["a"], e["b"])


@pytest.mark.parametrize("carry", ["none", "required", "either"])
@pytest.mark.parametrize("shape", [("row", 2), ("gap", 2), ("written", 2), ("row", 3), ("gap", 3)])
@pytest.mark.parametrize("decimals", [1, 2])
@pytest.mark.parametrize("high", [10, 20, 100, 1000, 1_000_000])
def test_a_block_of_decimals_fills_in_every_zahlenraum(high, decimals, carry, shape):
    format, numbers = shape
    out = generate(
        Settings(
            ops=["+", "-"],
            max=high,
            decimals=decimals,
            carry=carry,
            format=format,
            numbers=numbers,
            count=12,
            seed=1,
        )
    )
    assert len(out["exercises"]) == 12
    assert out["loosen"] is None


@pytest.mark.parametrize("carry", ["none", "required", "either"])
@pytest.mark.parametrize("shape", [("row", 2), ("gap", 2), ("written", 2), ("row", 3), ("gap", 3)])
def test_a_block_of_money_fills_in_a_hundred(carry, shape):
    format, numbers = shape
    out = generate(
        Settings(
            ops=["+", "-"],
            max=100,
            money=True,
            carry=carry,
            format=format,
            numbers=numbers,
            count=12,
            seed=1,
        )
    )
    assert len(out["exercises"]) == 12
    assert out["loosen"] is None


def test_the_written_form_sets_comma_under_comma_and_fills_with_zeros():
    assert text(written("+", 350, 125, 2)) == " 3,50\n+1,25\n\n-----\n 4,75"
    assert text(written("-", 1000, 5, 2)).split("\n")[:2] == [" 10,00", "~ 0,05"]


def test_a_decimal_carry_stands_in_the_units_column_not_on_the_comma():
    grid = written("+", 5, 5, 1)
    commas = {x for x, y, ch, kind in grid["cells"] if ch == ","}
    carry = [x for x, y, ch, kind in grid["cells"] if kind == CARRY]
    assert text(grid).split("\n")[2] == " 1"
    assert carry == [1] and not commas & set(carry)


def test_money_adds_a_euro_column_after_the_numbers():
    grid = written("+", 350, 125, 2, True)
    euros = sorted((x, y) for x, y, ch, kind in grid["cells"] if ch == "€")
    assert euros == [(5, 0), (5, 1), (5, 3)]
    assert grid["cols"] == 6 and grid["lines"][0][1] == 6


@given(
    st.sampled_from("+-"),
    st.integers(0, 10**6),
    st.integers(0, 10**6),
    st.integers(1, 2),
)
@settings(max_examples=100, deadline=None)
def test_the_written_decimal_answer_is_the_result(op, a, b, d):
    if op == "-":
        a, b = max(a, b), min(a, b)
    result = a + b if op == "+" else a - b
    grid = written(op, a, b, d)
    answer = "".join(ch for x, y, ch, kind in sorted(grid["cells"]) if kind == ANSWER and y == 3)
    whole, fraction = divmod(result, 10**d)
    assert answer == f"{whole},{fraction:0{d}d}"
    commas = [[x for x, y2, ch, kind in grid["cells"] if ch == "," and y2 == y] for y in (0, 1, 3)]
    assert all(len(c) == 1 for c in commas)
    assert len({c[0] for c in commas}) == 1


@pytest.mark.parametrize(
    "kw",
    [
        {"ops": ["*"], "format": "written"},
        {"ops": ["/"], "format": "gap"},
        {"ops": ["+", "*"], "format": "written"},
        {"ops": ["+", "-"], "format": "compare"},
        {"ops": ["+", "*"], "format": "row", "numbers": 3},
    ],
)
def test_times_divide_and_compare_take_no_decimals(kw):
    base = Settings(max=100, count=8, seed=3, **kw)
    with_decimals = Settings(max=100, count=8, seed=3, decimals=2, money=True, af=[(1, 2)], **kw)
    assert generate(with_decimals) == generate(base)


@pytest.mark.parametrize(
    "shape",
    [("row", 2), ("gap", 2), ("written", 2), ("row", 3), ("gap", 3), ("compare", 2)],
)
def test_a_seed_brings_the_same_decimal_tasks(shape):
    format, numbers = shape
    s = Settings(
        ops=["+", "-"],
        max=1000,
        decimals=2,
        format=format,
        numbers=numbers,
        count=10,
        seed=7,
    )
    assert generate(s) == generate(s)


@pytest.mark.parametrize(
    "shape",
    [("row", 2), ("gap", 2), ("written", 2), ("row", 3), ("gap", 3), ("compare", 2)],
)
def test_settings_without_decimals_come_out_as_before(shape):
    format, numbers = shape
    kw = {"ops": ["+", "-"], "max": 1000, "format": format, "numbers": numbers, "count": 10}
    plain = generate(Settings.model_validate({"seed": 5, **kw}))
    keys = {"decimals": 0, "af": [(1, 2)], "bf": [(3, 4)], "cf": [(5, 6)]}
    with_keys = generate(Settings.model_validate({"seed": 5, **keys, **kw}))
    assert with_keys == plain


def test_written_without_decimals_is_the_same_as_before():
    assert written("+", 557, 66) == written("+", 557, 66, 0, False)


@pytest.mark.parametrize(
    "shape",
    [("row", 2), ("gap", 2), ("written", 2), ("row", 3), ("gap", 3)],
)
@pytest.mark.parametrize("decimals", [1, 2])
def test_no_float_reaches_the_answer(shape, decimals):
    format, numbers = shape
    s = Settings(
        ops=["+", "-"],
        max=1000,
        decimals=decimals,
        money=decimals == 2,
        af=[(0, 9)],
        format=format,
        numbers=numbers,
        count=10,
        seed=2,
    )
    assert not any(isinstance(v, float) for v in walk(generate(s)))
