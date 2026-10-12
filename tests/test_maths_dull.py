"""Dull tasks: no two 0s or 1s in a Punkt vor Strich task, and no 0 in a written task."""

import pytest

from blattwerk.maths import Settings, generate, result

# The settings of #452: three numbers, Punkt vor Strich, brackets, max 100.
PVS = dict(ops=list("+-*/"), max=100, numbers=3, pvs=True, brackets=True, count=12)


def blocks(seeds=20, **limits):
    """One block of tasks for each seed."""
    return [generate(Settings(seed=seed, **limits))["exercises"] for seed in range(seeds)]


@pytest.mark.parametrize("fmt", ["row", "gap"])
def test_b1_no_task_of_three_holds_two_numbers_that_are_0_or_1(fmt):
    for block in blocks(**PVS, format=fmt):
        assert len(block) == 12
        for e in block:
            assert sum(e[k] in (0, 1) for k in "abc") <= 1, e


@pytest.mark.parametrize("fmt", ["row", "gap"])
def test_b2_no_bracket_comes_to_0_or_1(fmt):
    for block in blocks(**PVS, format=fmt):
        assert len(block) == 12
        for e in block:
            if e.get("paren") == "left":
                inner = result(e["op"], e["a"], e["b"])
            elif e.get("paren") == "right":
                inner = result(e["op2"], e["b"], e["c"])
            else:
                continue
            assert inner not in (0, 1), e


@pytest.mark.parametrize("fmt", ["row", "gap"])
def test_b3_at_most_one_result_of_0_in_a_block_of_12(fmt):
    for block in blocks(**PVS, format=fmt):
        assert len(block) == 12
        assert sum(e["result"] == 0 for e in block) <= 1, block


@pytest.mark.parametrize("ops", [["+", "-"], ["*", "/"]])
def test_c1_a_written_task_has_no_0_as_a_number(ops):
    for block in blocks(ops=ops, max=1000, format="written", count=12):
        for e in block:
            assert e["a"] != 0 and e["b"] != 0, e


def test_i7_tight_limits_still_fill_a_block_of_three():
    # Every number has digits 0 and 1 only: each task is dull, and the block still fills.
    digits = [(0, 1), (0, 0), (0, 0)]

    def tight():
        return blocks(
            5, ops=["+", "*"], max=100, numbers=3, pvs=True, count=6, a=digits, b=digits, c=digits
        )

    first = tight()
    # The unfixed code fills all six, for every seed.
    assert all(len(block) == 6 for block in first)
    assert tight() == first
