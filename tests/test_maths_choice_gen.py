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


def check_keep_out(ops, max, fmt, zero, one, distinct, count, seed):
    s = Settings(
        ops=ops,
        max=max,
        format=fmt,
        zero=zero,
        one=one,
        distinct=distinct,
        count=count,
        seed=seed,
    )
    for e in generate(s)["exercises"]:
        a, b, result, op = e["a"], e["b"], e["result"], e["op"]
        if not zero:
            assert 0 not in (a, b) and result != 0
        if not one and op == "*":
            assert 1 not in (a, b)
        if not one and op == "/":
            assert b != 1
        if distinct:
            assert a != b


@settings(max_examples=100, deadline=1000)
@given(
    ops=OPS,
    max=st.sampled_from(FAST_ROOMS),
    fmt=st.sampled_from(["row", "gap", "written"]),
    zero=st.booleans(),
    one=st.booleans(),
    distinct=st.booleans(),
    count=st.integers(1, 6),
    seed=st.integers(0, 10**9),
)
def test_the_switches_keep_their_numbers_out_rooms_10_20_1000_1000000(
    ops, max, fmt, zero, one, distinct, count, seed
):
    check_keep_out(ops, max, fmt, zero, one, distinct, count, seed)


@settings(max_examples=100, deadline=1000)
@given(
    ops=st.sampled_from([["+"], ["-"], ["*"], ["/"]]),
    fmt=st.sampled_from(["row", "gap", "written"]),
    switch=ONE_SWITCH,
    count=st.integers(1, 6),
    seed=st.integers(0, 10**9),
)
def test_the_switches_keep_their_numbers_out_room_100(ops, fmt, switch, count, seed):
    check_keep_out(
        ops,
        100,
        fmt,
        switch.get("zero", True),
        switch.get("one", True),
        switch.get("distinct", False),
        count,
        seed,
    )


@settings(max_examples=100, deadline=1000)
@given(
    ops=OPS,
    max=st.sampled_from([10, 20, 100, 1000]),
    fmt=st.sampled_from(["row", "gap"]),
    zero=st.booleans(),
    one=st.booleans(),
    distinct=st.booleans(),
    count=st.integers(1, 8),
    seed=st.integers(0, 10**9),
)
def test_the_switches_keep_their_numbers_out_of_three(
    ops, max, fmt, zero, one, distinct, count, seed
):
    s = Settings(
        ops=ops,
        max=max,
        numbers=3,
        format=fmt,
        zero=zero,
        one=one,
        distinct=distinct,
        count=count,
        seed=seed,
    )
    for e in generate(s)["exercises"]:
        nums = [e["a"], e["b"], e["c"]]
        if not zero:
            assert 0 not in nums and e["result"] != 0
        if distinct:
            assert len(set(nums)) == 3
        if not one:
            right = e["paren"] == "right" if "paren" in e else e["op2"] in "*/" and e["op"] in "+-"
            of_op = [e["a"]] + ([] if right else [e["b"]])
            of_op2 = [e["c"]] + ([e["b"]] if right else [])
            if e["op"] == "*":
                assert 1 not in of_op
            if e["op2"] == "*":
                assert 1 not in of_op2
            if e["op"] == "/" and not right:
                assert e["b"] != 1
            if e["op2"] == "/":
                assert e["c"] != 1


@settings(max_examples=100, deadline=1000)
@given(
    sides=st.sampled_from(["nn", "tn", "tt"]),
    ops=OPS,
    zero=st.booleans(),
    one=st.booleans(),
    distinct=st.booleans(),
    count=st.integers(1, 12),
    seed=st.integers(0, 10**9),
)
def test_the_switches_hold_in_a_comparison(sides, ops, zero, one, distinct, count, seed):
    s = Settings(
        ops=ops,
        max=100,
        format="compare",
        sides=sides,
        zero=zero,
        one=one,
        distinct=distinct,
        count=count,
        seed=seed,
    )
    for e in generate(s)["exercises"]:
        for side in (e["left"], e["right"]):
            if not zero:
                assert side["value"] != 0
            if "op" in side:
                if not zero:
                    assert 0 not in (side["a"], side["b"])
                if not one and side["op"] == "*":
                    assert 1 not in (side["a"], side["b"])
                if not one and side["op"] == "/":
                    assert side["b"] != 1
                if distinct:
                    assert side["a"] != side["b"]


def check_fill(max, ops, fmt, gaps, seed):
    s = Settings(ops=ops, max=max, format=fmt, gaps=gaps, count=12, seed=seed)
    out = generate(s)
    assert len(out["exercises"]) == 12, s
    assert out["loosen"] is None, s


@settings(max_examples=100, deadline=1000)
@given(
    max=st.sampled_from(FAST_ROOMS),
    ops=OPS,
    fmt=st.sampled_from(["row", "gap"]),
    gaps=GAPS,
    seed=st.integers(0, 10**9),
)
def test_every_two_number_block_fills_in_rooms_10_20_1000_1000000(max, ops, fmt, gaps, seed):
    check_fill(max, ops, fmt, gaps, seed)


@settings(max_examples=100, deadline=1000)
@given(
    ops=OPS,
    fmt=st.sampled_from(["row", "gap"]),
    gaps=GAPS,
    seed=st.integers(0, 10**9),
)
def test_every_two_number_block_fills_in_room_100(ops, fmt, gaps, seed):
    check_fill(100, ops, fmt, gaps, seed)


@settings(max_examples=100, deadline=1000)
@given(
    max=st.sampled_from(FAST_ROOMS),
    ops=OPS,
    gaps=GAPS,
    seed=st.integers(0, 10**9),
)
def test_every_written_block_fills_in_rooms_10_20_1000_1000000(max, ops, gaps, seed):
    check_fill(max, ops, "written", gaps, seed)


@settings(max_examples=100, deadline=1000)
@given(
    ops=OPS,
    gaps=GAPS,
    seed=st.integers(0, 10**9),
)
def test_every_written_block_fills_in_room_100(ops, gaps, seed):
    check_fill(100, ops, "written", gaps, seed)


@settings(max_examples=100, deadline=1000)
@given(
    max=st.sampled_from(ROOMS),
    ops=OPS,
    fmt=st.sampled_from(["row", "gap"]),
    gaps=GAPS,
    seed=st.integers(0, 10**9),
)
def test_every_three_number_block_fills_in_every_zahlenraum_of_the_panel(max, ops, fmt, gaps, seed):
    s = Settings(ops=ops, max=max, format=fmt, numbers=3, gaps=gaps, count=12, seed=seed)
    out = generate(s)
    assert len(out["exercises"]) == 12, s
    assert out["loosen"] is None, s


def brute(op, max, zero, one, distinct):
    """The tasks with two numbers up to max that keep the limits, counted by hand."""
    n = 0
    for a in range(max + 1):
        for b in range(max + 1):
            if op == "+":
                r = a + b
                if r > max:
                    continue
            elif op == "-":
                if b > a:
                    continue
                r = a - b
            elif op == "*":
                r = a * b
                if r > max:
                    continue
            else:
                if b == 0 or a % b:
                    continue
                r = a // b
            if not zero and (0 in (a, b) or r == 0):
                continue
            if not one and ((op == "*" and 1 in (a, b)) or (op == "/" and b == 1)):
                continue
            if distinct and a == b:
                continue
            n += 1
    return n


@settings(max_examples=100, deadline=1000)
@given(
    op=st.sampled_from(["+", "-", "*", "/"]),
    max=st.integers(1, 20),
    zero=st.booleans(),
    one=st.booleans(),
    distinct=st.booleans(),
    count=st.integers(1, 40),
    seed=st.integers(0, 10**9),
)
def test_a_switch_misses_no_task_in_a_small_zahlenraum(op, max, zero, one, distinct, count, seed):
    s = Settings(
        ops=[op],
        max=max,
        rest=False,
        format="row",
        zero=zero,
        one=one,
        distinct=distinct,
        count=count,
        seed=seed,
    )
    out = generate(s)
    have = brute(op, max, zero, one, distinct)
    assert len(out["exercises"]) == min(count, have)
    if len(out["exercises"]) < count:
        for name, on in (("zero", zero), ("one", one), ("distinct", distinct)):
            default = {"zero": True, "one": True, "distinct": False}[name]
            if on == default:
                continue
            loose = brute(
                op,
                max,
                zero or name == "zero",
                one or name == "one",
                distinct and name != "distinct",
            )
            if min(count, loose) > len(out["exercises"]):
                assert name in out["loosen"]


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


def loose_here(op, a, b, k):
    """Whether any number fits the gap k, worked out in the test."""
    if k == "a":
        return op == "*" and b == 0
    if k == "b":
        return (op == "*" and a == 0) or (op == "/" and a // b == 0)
    return False


def check_only_ticked(ops, max, gaps, rest, zero, one, distinct, count, seed):
    s = Settings(
        ops=ops,
        max=max,
        format="gap",
        gaps=gaps,
        rest=rest,
        zero=zero,
        one=one,
        distinct=distinct,
        count=count,
        seed=seed,
    )
    ticked = gaps or ["a", "b", "c"]
    allowed = [k for k in ("a", "b", "result") if k in ticked] or ["a", "b"]
    for e in generate(s)["exercises"]:
        hide = e.get("hide", "result")
        assert hide in allowed, e
        if hide in ("a", "b"):
            assert not loose_here(e["op"], e["a"], e["b"], hide), e


@settings(max_examples=100, deadline=1000)
@given(
    ops=OPS,
    max=st.sampled_from([10, 20, 1000, 1_000_000]),
    gaps=st.lists(st.sampled_from(["a", "b", "result"]), min_size=1, unique=True),
    rest=st.booleans(),
    zero=st.booleans(),
    one=st.booleans(),
    distinct=st.booleans(),
    count=st.integers(1, 8),
    seed=st.integers(0, 10**9),
)
def test_a_set_gap_hides_only_what_is_ticked(
    ops, max, gaps, rest, zero, one, distinct, count, seed
):
    check_only_ticked(ops, max, gaps, rest, zero, one, distinct, count, seed)


@settings(max_examples=100, deadline=1000)
@given(
    ops=st.sampled_from([["+"], ["-"], ["*"], ["/"]]),
    gaps=st.lists(st.sampled_from(["a", "b", "result"]), min_size=1, unique=True),
    count=st.integers(1, 8),
    seed=st.integers(0, 10**9),
)
def test_a_set_gap_hides_only_what_is_ticked_room_100(ops, gaps, count, seed):
    check_only_ticked(ops, 100, gaps, False, True, True, False, count, seed)


@settings(max_examples=100, deadline=1000)
@given(
    ops=OPS,
    max=st.sampled_from([10, 20, 100]),
    pvs=st.booleans(),
    brackets=st.booleans(),
    gaps=st.lists(st.sampled_from(["a", "b", "c", "result"]), min_size=1, unique=True),
    count=st.integers(1, 6),
    seed=st.integers(0, 10**9),
)
def test_a_set_gap_of_three_numbers_hides_only_what_is_ticked(
    ops, max, pvs, brackets, gaps, count, seed
):
    s = Settings(
        ops=ops,
        max=max,
        numbers=3,
        format="gap",
        gaps=gaps,
        pvs=pvs,
        brackets=brackets,
        count=count,
        seed=seed,
    )
    ticked = gaps or ["a", "b", "c"]
    allowed = [k for k in ("a", "b", "c", "result") if k in ticked] or ["a", "b", "c"]
    for e in generate(s)["exercises"]:
        assert e.get("hide", "result") in allowed, e


def test_a_set_gap_of_three_numbers_hides_no_other_number_where_zeros_are_many():
    # Thirty times tasks up to 5 need tasks with a 0, where the first number is not told.
    s = Settings(ops=["*"], max=5, numbers=3, format="gap", gaps=["a"], count=30, seed=0)
    exercises = generate(s)["exercises"]
    assert exercises
    for e in exercises:
        assert e.get("hide") == "a", e
        fits = [x for x in range(6) if x * e["b"] * e["c"] == e["result"]]
        assert fits == [e["a"]], e


def test_digits_that_leave_only_open_gaps_give_no_task_of_three_numbers():
    s = Settings(ops=["*"], max=1000, numbers=3, format="gap", gaps=["b"], count=20, seed=1)
    s = s.model_copy(update={"a": [(0, 0)] * 4})
    assert generate(s) == {"exercises": [], "loosen": ["a"]}


def test_a_set_gap_of_a_times_task_never_hides_a_zero_factor_as_b():
    s = Settings(ops=["*"], max=10, format="gap", gaps=["a"], count=12, seed=0)
    exercises = generate(s)["exercises"]
    assert exercises
    for e in exercises:
        assert e.get("hide") == "a", e
        assert e["b"] != 0, e


@settings(max_examples=100, deadline=1000)
@given(
    max=st.sampled_from(ROOMS),
    ops=OPS,
    count=st.integers(1, 12),
    seed=st.integers(0, 10**9),
)
def test_no_equal_numbers_in_a_comparison_of_two_numbers(max, ops, count, seed):
    s = Settings(
        ops=ops,
        max=max,
        format="compare",
        sides="nn",
        equal="some",
        distinct=True,
        count=count,
        seed=seed,
    )
    for e in generate(s)["exercises"]:
        assert e["left"]["value"] != e["right"]["value"], e
