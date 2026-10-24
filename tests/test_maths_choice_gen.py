import json
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from blattwerk.maths import Settings, generate

ROOMS = [10, 20, 100, 1000, 1_000_000]
# The Zahlenraum 100 is slow: each call makes about 10 thousand pairs, so it has its own tests.
FAST_ROOMS = [10, 20, 1000, 1_000_000]
GOLDEN = json.loads((Path(__file__).parent / "maths_before_73.json").read_text())


def check_golden(cases):
    for case in cases:
        assert generate(Settings(**case["settings"])) == case["made"], case["settings"]


def test_old_settings_make_what_they_made_before_the_gap_choice_part_1():
    check_golden(GOLDEN[0::3])


def test_old_settings_make_what_they_made_before_the_gap_choice_part_2():
    check_golden(GOLDEN[1::3])


def test_old_settings_make_what_they_made_before_the_gap_choice_part_3():
    check_golden(GOLDEN[2::3])


GAPS = st.none() | st.lists(st.sampled_from(["a", "b", "c", "result"]), min_size=1, unique=True)
OPS = st.lists(st.sampled_from("+-*/"), min_size=1, max_size=4, unique=True)


def calc(op, x, y):
    """A step worked out by hand: None for a division that does not come out even."""
    if op == "/":
        return x // y if y and x % y == 0 else None
    return {"+": x + y, "-": x - y, "*": x * y}[op]


def three_result(e):
    """The result of a three-number task, worked out by hand."""
    op, op2, a, b, c = e["op"], e["op2"], e["a"], e["b"], e["c"]
    right = e["paren"] == "right" if "paren" in e else op2 in "*/" and op in "+-"
    if right:
        w = calc(op2, b, c)
        return None if w is None else calc(op, a, w)
    v = calc(op, a, b)
    return None if v is None else calc(op2, v, c)


def unfair(op, a, b, result, k):
    """Whether any number fits the gap k, so k may not be hidden."""
    if k == "a":
        return op == "*" and b == 0
    if k == "b":
        return (op == "*" and a == 0) or (op == "/" and result == 0)
    return False


def check_every_result(ops, max, gaps, zero, one, distinct, rest, count, seed):
    s = Settings(
        ops=ops,
        max=max,
        format="gap",
        gaps=gaps,
        zero=zero,
        one=one,
        distinct=distinct,
        rest=rest,
        count=count,
        seed=seed,
    )
    out = generate(s)
    assert out == generate(s)
    ticked = gaps or ["a", "b", "c"]
    allowed = [k for k in ("a", "b", "result") if k in ticked] or ["a", "b"]
    for e in out["exercises"]:
        op, a, b, result = e["op"], e["a"], e["b"], e["result"]
        if op == "/":
            assert b > 0
            assert a == result * b + e["rest"] and 0 <= e["rest"] < b
        else:
            assert e["rest"] == 0
            assert result == calc(op, a, b)
        hide = e.get("hide", "result")
        assert hide in ("a", "b", "result")
        # The ticked gaps are kept, unless every one of them is unfair for this task.
        assert hide in allowed or all(unfair(op, a, b, result, k) for k in allowed)


@settings(max_examples=100, deadline=1000)
@given(
    ops=OPS,
    max=st.sampled_from(FAST_ROOMS),
    gaps=GAPS,
    zero=st.booleans(),
    one=st.booleans(),
    distinct=st.booleans(),
    rest=st.booleans(),
    count=st.integers(1, 6),
    seed=st.integers(0, 10**9),
)
def test_every_result_is_right_and_the_gap_hides_what_is_ticked_rooms_10_20_1000_1000000(
    ops, max, gaps, zero, one, distinct, rest, count, seed
):
    check_every_result(ops, max, gaps, zero, one, distinct, rest, count, seed)


# One switch off its default at a time, so the examples share their limits and the cache hits.
ONE_SWITCH = st.sampled_from([{}, {"zero": False}, {"one": False}, {"distinct": True}])


@settings(max_examples=100, deadline=1000)
@given(
    ops=st.sampled_from([["+"], ["-"], ["*"], ["/"]]),
    gaps=GAPS,
    switch=ONE_SWITCH,
    count=st.integers(1, 6),
    seed=st.integers(0, 10**9),
)
def test_every_result_is_right_and_the_gap_hides_what_is_ticked_room_100(
    ops, gaps, switch, count, seed
):
    check_every_result(
        ops,
        100,
        gaps,
        switch.get("zero", True),
        switch.get("one", True),
        switch.get("distinct", False),
        False,
        count,
        seed,
    )


@settings(max_examples=100, deadline=1000)
@given(
    ops=OPS,
    max=st.sampled_from([10, 20]),
    gaps=GAPS,
    seed=st.integers(0, 10**9),
    count=st.integers(1, 6),
)
def test_the_hidden_number_is_the_only_one_that_fits_rooms_10_20(ops, max, gaps, seed, count):
    check_hidden(ops, max, gaps, seed, count)


@settings(max_examples=100, deadline=1000)
@given(
    ops=OPS,
    gaps=GAPS,
    seed=st.integers(0, 10**9),
    count=st.integers(1, 4),
)
def test_the_hidden_number_is_the_only_one_that_fits_room_100(ops, gaps, seed, count):
    check_hidden(ops, 100, gaps, seed, count)


def check_hidden(ops, max, gaps, seed, count):
    s = Settings(ops=ops, max=max, format="gap", gaps=gaps, rest=False, count=count, seed=seed)
    for e in generate(s)["exercises"]:
        hide = e.get("hide", "result")
        if hide not in ("a", "b"):
            continue
        op, a, b, result = e["op"], e["a"], e["b"], e["result"]
        fits = 0
        # A number of the task never lies above the Zahlenraum, so no try goes beyond it.
        for x in range(0, max + 1):
            if hide == "a":
                if op == "/":
                    fits += b > 0 and x % b == 0 and x // b == result
                else:
                    fits += calc(op, x, b) == result
            else:
                if op == "/":
                    fits += x > 0 and a % x == 0 and a // x == result
                else:
                    fits += calc(op, a, x) == result
        assert fits == 1, e


@settings(max_examples=100, deadline=1000)
@given(
    ops=OPS,
    max=st.sampled_from([10, 20, 100, 1000]),
    fmt=st.sampled_from(["row", "gap"]),
    gaps=GAPS,
    zero=st.booleans(),
    one=st.booleans(),
    distinct=st.booleans(),
    pvs=st.booleans(),
    brackets=st.booleans(),
    count=st.integers(1, 8),
    seed=st.integers(0, 10**9),
)
def test_three_numbers_hide_what_is_ticked_and_come_out_right(
    ops, max, fmt, gaps, zero, one, distinct, pvs, brackets, count, seed
):
    s = Settings(
        ops=ops,
        max=max,
        numbers=3,
        format=fmt,
        gaps=gaps,
        zero=zero,
        one=one,
        distinct=distinct,
        pvs=pvs,
        brackets=brackets,
        count=count,
        seed=seed,
    )
    out = generate(s)
    for e in out["exercises"]:
        assert three_result(e) == e["result"]
        assert e.get("hide", "result") in ("a", "b", "c", "result")
        if gaps == ["result"]:
            assert "hide" not in e


def test_gap_of_result_alone_hides_no_number():
    s = Settings(ops=["+", "-"], max=20, format="gap", gaps=["result"], count=12, seed=3)
    for e in generate(s)["exercises"]:
        assert "hide" not in e


def test_a_and_result_mix_hidden_and_unhidden_gaps():
    for seed in range(21):
        s = Settings(ops=["+"], max=20, format="gap", gaps=["a", "result"], count=12, seed=seed)
        exercises = generate(s)["exercises"]
        hidden = [e.get("hide") == "a" for e in exercises]
        if any(hidden) and not all(hidden):
            assert any("hide" not in e for e in exercises)
            return
    raise AssertionError("no seed mixed the gaps")


def test_b_gap_hides_only_b():
    s = Settings(ops=["+"], max=20, format="gap", gaps=["b"], count=12, seed=5)
    exercises = generate(s)["exercises"]
    assert exercises and all(e["hide"] == "b" for e in exercises)


def test_decimals_in_a_big_zahlenraum_with_few_digits_still_make_their_tasks():
    narrow = {"a": [[0, 1]] + [[0, 0]] * 6, "b": [[0, 1]] + [[0, 0]] * 6, "af": [[0, 1], [0, 0]]}
    narrow["bf"] = narrow["af"]
    a, b, af = narrow["a"], narrow["b"], narrow["af"]
    for s in (
        Settings(
            ops=["+", "-"], count=6, seed=1, a=a, b=b, af=af, bf=af, max=1_000_000, money=True
        ),
        Settings(ops=["+", "-"], count=6, seed=1, a=a, b=b, af=af, bf=af, max=100_000, decimals=2),
        Settings(
            ops=["+", "-"], count=6, seed=1, a=a, b=b, af=af, bf=af, max=1_000_000, decimals=1
        ),
    ):
        assert len(generate(s)["exercises"]) == 6, s


@settings(max_examples=100, deadline=1000)
@given(
    max=st.sampled_from(ROOMS),
    decimals=st.sampled_from([0, 1, 2]),
    money=st.booleans(),
    ops=st.lists(st.sampled_from("+-"), min_size=1, max_size=2, unique=True),
    narrow_a=st.booleans(),
    narrow_b=st.booleans(),
    fmt=st.sampled_from(["row", "gap", "written"]),
    count=st.integers(1, 6),
    seed=st.integers(0, 10**9),
)
def test_decimals_and_geld_make_tasks_in_every_zahlenraum(
    max, decimals, money, ops, narrow_a, narrow_b, fmt, count, seed
):
    s = Settings(
        ops=ops,
        max=max,
        decimals=decimals,
        money=money,
        a=[[0, 1]] * 7 if narrow_a else [],
        b=[[0, 1]] * 7 if narrow_b else [],
        af=[[0, 1], [0, 0]] if narrow_a else [],
        bf=[[0, 1], [0, 0]] if narrow_b else [],
        format=fmt,
        count=count,
        seed=seed,
    )
    for e in generate(s)["exercises"]:
        assert e["result"] == (e["a"] + e["b"] if e["op"] == "+" else e["a"] - e["b"])
