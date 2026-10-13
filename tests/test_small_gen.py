import json
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from blattwerk.maths import Settings, generate

GOLDEN = json.loads((Path(__file__).parent / "maths_before_451.json").read_text())

OPS = st.lists(st.sampled_from("+-*/"), min_size=1, max_size=4, unique=True)
TIMES_OR_DIVIDE = st.lists(st.sampled_from("*/"), min_size=1, max_size=2, unique=True)


def factors_and_quotient_ok(e):
    """Whether a times or divide exercise of the sheet is of the kleine Einmaleins."""
    if e["op"] == "*":
        return 1 <= e["a"] <= 10 and 1 <= e["b"] <= 10
    if e["op"] == "/":
        return 1 <= e["b"] <= 10 and 1 <= e["a"] // e["b"] <= 10
    return True


@settings(max_examples=100, deadline=None)
@given(
    ops=OPS,
    max_=st.sampled_from([20, 100, 1000]),
    format_=st.sampled_from(["row", "gap", "written"]),
    one=st.booleans(),
    zero=st.booleans(),
    rest=st.sampled_from([False, True]),
    family=st.sampled_from(["none", "swap", "reverse", "neighbour"]),
    count=st.integers(1, 10),
    seed=st.integers(0, 99),
)
def test_every_times_and_divide_task_is_of_the_kleine_einmaleins(
    ops, max_, format_, one, zero, rest, family, count, seed
):
    s = Settings(
        ops=ops,
        max=max_,
        format=format_,
        one=one,
        zero=zero,
        rest=rest,
        family=family,
        count=count,
        seed=seed,
        small=True,
    )
    for e in generate(s)["exercises"]:
        if e["op"] not in "*/":
            continue
        assert factors_and_quotient_ok(e), e
        assert 0 not in (e["a"], e["b"], e["result"]), e
        if not one:
            assert 1 not in (e["a"], e["b"]), e
            assert e["op"] == "*" or e["a"] // e["b"] >= 2, e


@settings(max_examples=100, deadline=None)
@given(
    ops=st.sampled_from([["/"], ["*"]]),
    max_=st.sampled_from([100, 1000, 1_000_000]),
    count=st.integers(1, 20),
    seed=st.integers(0, 99),
)
def test_the_kleine_einmaleins_fills_the_block_in_any_zahlenraum(ops, max_, count, seed):
    out = generate(Settings(ops=ops, max=max_, count=count, seed=seed, small=True))
    assert len(out["exercises"]) == count
    assert out["loosen"] is None


@settings(max_examples=100, deadline=None)
@given(
    ops=TIMES_OR_DIVIDE,
    sides=st.sampled_from(["tn", "tt"]),
    one=st.booleans(),
    count=st.integers(1, 10),
    seed=st.integers(0, 99),
)
def test_comparisons_keep_to_the_kleine_einmaleins(ops, sides, one, count, seed):
    s = Settings(ops=ops, max=100, format="compare", sides=sides, one=one, count=count, seed=seed)
    out = generate(s.model_copy(update={"small": True}))
    for e in out["exercises"]:
        for term in e.values():
            if isinstance(term, dict) and term.get("op") in ("*", "/"):
                assert factors_and_quotient_ok(term), term
                if not one:
                    assert 1 not in (term["a"], term["b"]), term
                    assert term["op"] == "*" or term["a"] // term["b"] >= 2, term


def test_too_few_tasks_name_the_switch():
    out = generate(Settings(ops=["*"], one=False, count=100, max=100, seed=1, small=True))
    assert len(out["exercises"]) < 100
    assert "small" in out["loosen"]


@settings(max_examples=100, deadline=None)
@given(seed=st.integers(0, 99), fmt=st.sampled_from(["row", "gap"]))
def test_three_numbers_ignore_the_switch(seed, fmt):
    def make(small: bool):
        return generate(
            Settings(
                ops=["+", "*", "/"], max=100, count=8, seed=seed, numbers=3, format=fmt, small=small
            )
        )

    assert make(True) == make(False)


def test_off_draws_what_master_drew():
    for case, made in GOLDEN:
        assert generate(Settings(**case)) == made, case
        assert generate(Settings(**case, small=False)) == made, case
