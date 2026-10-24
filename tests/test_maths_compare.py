"""Comparisons the maths generator makes: limits, seeds, and a division that comes out even.

The helpers live in test_maths.py.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from test_maths import (
    in_places,
    keeps,
    places,
    settings_for,
)

from blattwerk.maths import (
    Settings,
    generate,
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


@given(compares)
# Each example runs the generator's full try budget several times: 100 took 13 to 23 s here and
# ran out of the 50 s of a busy CI shard once.
@settings(max_examples=60, deadline=None)
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
