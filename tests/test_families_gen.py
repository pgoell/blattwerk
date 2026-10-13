from hypothesis import given, settings
from hypothesis import strategies as st
from test_maths import keeps, places

from blattwerk.maths import Settings, generate, scaled, school

MAX = st.sampled_from([10, 20, 100, 1000, 1_000_000]) | st.integers(1, 1_000_000)
CARRY = st.sampled_from(["none", "required", "either"])
FAMILY = st.sampled_from(["swap", "reverse", "neighbour"])
MOVES = st.sampled_from(["a", "b"])

families = st.builds(
    Settings,
    ops=st.lists(st.sampled_from("+-*/"), min_size=1, max_size=4),
    max=MAX,
    a=places,
    b=places,
    carry=CARRY,
    rest=st.booleans(),
    format=st.sampled_from(["row", "gap"]),
    family=FAMILY,
    moves=MOVES,
    decimals=st.sampled_from([0, 0, 1, 2]),
    money=st.booleans(),
    count=st.integers(1, 12),
    seed=st.integers(0, 10**9),
)
blocks = st.builds(
    Settings,
    ops=st.lists(st.sampled_from("+-*/"), min_size=1, max_size=4),
    # The rooms the panel offers.
    max=st.sampled_from([10, 20, 100, 1000, 1_000_000]),
    format=st.sampled_from(["row", "gap"]),
    family=FAMILY,
    moves=MOVES,
    count=st.integers(1, 12),
    seed=st.integers(0, 10**9),
)
single = st.builds(
    Settings,
    ops=st.sampled_from([["+"], ["-"], ["*"], ["/"]]),
    max=st.integers(1, 20),
    carry=CARRY,
    rest=st.just(False),
    format=st.sampled_from(["row", "gap"]),
    family=FAMILY,
    moves=MOVES,
    count=st.integers(1, 30),
    seed=st.integers(0, 10**9),
)


def value(op, a, b):
    """What a task comes to, worked out here."""
    if op == "/":
        return a // b
    return {"+": a + b, "-": a - b, "*": a * b}[op]


def expected(kind, moves, op, a, b):
    """The tasks of a family, in order, from its drawn task: worked out here from the rules."""
    if kind == "swap":
        return [(op, a, b), (op, b, a)]
    if kind == "reverse":
        return [(op, a, b), ({"+": "-", "-": "+", "*": "/", "/": "*"}[op], value(op, a, b), b)]
    if op == "/" and moves == "a":
        return [(op, a, b), (op, a - b, b), (op, a + b, b)]
    if moves == "a":
        return [(op, a, b), (op, a - 1, b), (op, a + 1, b)]
    return [(op, a, b), (op, a, b - 1), (op, a, b + 1)]


def task(op, a, b):
    """One task as a dict, its result and rest worked out here (b is never 0 for a divide)."""
    if op == "/":
        return {"op": op, "a": a, "b": b, "result": a // b, "rest": a % b}
    return {"op": op, "a": a, "b": b, "result": value(op, a, b), "rest": 0}


def members(kind, moves, op, a, b):
    """The tasks of the family of one task, or [] when it has none, worked out here."""
    if kind == "swap":
        return [] if a == b else expected(kind, moves, op, a, b)
    return expected(kind, moves, op, a, b)


def holds(s, op, a, b):
    """Whether one task of a family keeps the limits, with no rest when `rest` is False."""
    if a < 0 or b < 0 or (op == "/" and b == 0) or (op == "-" and a < b):
        return False
    t = task(op, a, b)
    return keeps(s, t) and (op != "/" or t["rest"] == 0)


@given(families)
@settings(max_examples=12, deadline=None)
def test_every_task_of_a_family_keeps_every_limit_and_its_result_is_right(s):
    out = generate(s)
    exercises = out["exercises"]
    if s.family == "swap" and not {"+", "*"} & set(s.ops):
        assert all("family" not in e for e in exercises)
        return
    kind = s.family
    for e in exercises:
        # With places after the comma the tasks come in whole numbers of the smallest place.
        t = scaled(s).model_copy(update={"ops": [*s.ops, e["op"]]})
        assert keeps(t, e)
        if kind == "reverse":
            assert e["rest"] == 0
        elif e["op"] == "/":
            assert (e["rest"] > 0) == bool(s.rest)
        if s.format == "gap" and e["op"] == "*" and e["a"] == e["b"] == 0:
            assert "hide" not in e
        elif s.format == "gap":
            assert e["hide"] in ("a", "b")
        else:
            assert "hide" not in e
    numbers = [e["family"] for e in exercises]
    assert numbers == sorted(numbers)
    assert sorted(set(numbers)) == list(range(len(set(numbers))))
    found = []
    for n in sorted(set(numbers)):
        fam = [(e["op"], e["a"], e["b"]) for e in exercises if e["family"] == n]
        size = 2 if kind in ("swap", "reverse") else 3
        assert len(fam) == size
        assert fam == expected(kind, s.moves, *fam[0])
        assert len(set(fam)) == len(fam)
        found.append(frozenset(fam))
    assert len(set(found)) == len(found)
    assert len(found) <= s.count
    assert (out["loosen"] is None) == (len(found) == s.count)
    tasks = [(e["op"], e["a"], e["b"]) for e in exercises]
    assert len(set(tasks)) == len(tasks)
    assert generate(s) == out


@given(blocks)
@settings(max_examples=70, deadline=None)
def test_every_block_fills_in_every_zahlenraum_of_the_panel(s):
    s = s.model_copy(update={"carry": "either", "rest": False})
    out = generate(s)
    if s.family == "swap" and not {"+", "*"} & set(s.ops):
        assert len(out["exercises"]) == s.count
        assert out["loosen"] is None
        return
    # A block may come short, and then it says so.
    numbers = len({e["family"] for e in out["exercises"]})
    assert (numbers == s.count and out["loosen"] is None) or (
        numbers < s.count and out["loosen"] is not None
    )


@given(single)
@settings(max_examples=250, deadline=None)
def test_no_family_is_missed_in_a_small_zahlenraum(s):
    op = s.ops[0]
    if s.family == "swap" and op not in "+*":
        assert all("family" not in e for e in generate(s)["exercises"])
        return
    seen: dict[frozenset, tuple] = {}  # family -> its drawn task
    wide = s.model_copy(update={"ops": list("+-*/")})
    for a in range(s.max + 1):
        for b in range(s.max + 1):
            if op == "/" and b == 0:
                continue
            if s.family == "swap" and a == b:
                continue
            fam = members(s.family, s.moves, op, a, b)
            if not fam:
                continue
            if all(holds(wide, *t) for t in fam):
                seen.setdefault(frozenset(fam), tuple(fam[0]))
    distinct = len(seen)
    exercises = generate(s)["exercises"]
    got = {e["family"] for e in exercises}
    assert len(got) <= min(s.count, distinct)
    if s.family != "neighbour" or len(got) == s.count:
        return
    # Short of the count, a family that shares no task with the block is refused only as a
    # plain one, and only once the plain share is full.
    used = {(e["op"], e["a"], e["b"]) for e in exercises}
    # The drawn task of each family in the block is its first exercise.
    drawn = {}
    for e in exercises:
        drawn.setdefault(e["family"], (e["op"], e["a"], e["b"]))
    block_plain = sum(1 for t in drawn.values() if t[0] in "*/" and not school(*t))
    for fam, first in seen.items():
        if fam & used:
            continue
        assert first[0] in "*/" and not school(*first)
        assert block_plain == s.count // 10


def test_a_gap_of_nothing_times_nothing_hides_its_result():
    out = generate(Settings(ops=["*"], max=1, format="gap", count=4, seed=0))
    assert len(out["exercises"]) == 4
    zero = next(e for e in out["exercises"] if e["a"] == e["b"] == 0)
    assert "hide" not in zero
