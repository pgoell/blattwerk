"""Exercises of three numbers: a term worked in two steps."""

import random
from math import isqrt

from blattwerk.maths.compare import aimed
from blattwerk.maths.model import Range, Settings, fits, gaps_of, loosened, pick, plain
from blattwerk.maths.pairs import bound, carries, propose, result, valid


def step(s: Settings, op: str, x: int, y: int, top: int) -> int | None:
    """What one step comes to, or None when it breaks a limit: a remainder, a carry, or a result."""
    if op == "/" and (y == 0 or x % y):
        return None
    if op in "+-" and s.carry != "either" and (s.carry == "required") != any(carries(op, x, y)):
        return None
    r = result(op, x, y)
    return r if 0 <= r <= top else None


def worked(s: Settings, e: dict, top: int) -> int | None:
    """The result of a three-number exercise, worked step by step, or None if a step fails."""
    op, op2, a, b, c = e["op"], e["op2"], e["a"], e["b"], e["c"]
    # Brackets say what goes first. Else a Punkt step goes first; equal kinds run left to right.
    right = e["paren"] == "right" if "paren" in e else op2 in "*/" and op in "+-"
    if right:
        w = step(s, op2, b, c, top)
        return None if w is None else step(s, op, a, w, top)
    v = step(s, op, a, b, top)
    return None if v is None else step(s, op2, v, c, top)


def sound(s: Settings, e: dict, top: int) -> bool:
    """Whether a three-number exercise keeps every limit, and its result is right."""
    fit = all(fits(ranges, n) for ranges, n in ((s.a, e["a"]), (s.b, e["b"]), (s.c, e["c"])))
    inside = max(e["a"], e["b"], e["c"]) <= s.max and e["op"] in s.ops and e["op2"] in s.ops
    return fit and inside and plain(s, e) and worked(s, e, top) == e["result"]


def calm(ranges: list[Range], other: int, op: str, first: bool = False) -> list[Range] | None:
    """The digit ranges narrowed so the number makes no carry with `other`, or None when a place
    has no digit left. For "-", `first` says whether the number is the one taken from."""
    if op == "-" and first and other >= 10 ** len(ranges):
        return None
    out: list[Range] = []
    for i, (lo, hi) in enumerate(ranges):
        d = other // 10**i % 10
        if op == "+":
            hi = min(hi, 9 - d)
        elif first:
            lo = max(lo, d)
        else:
            hi = min(hi, d)
        if lo > hi:
            return None
        out.append((lo, hi))
    return out


def once(s: Settings, op: str, top: int, rng: random.Random) -> tuple[int, int] | None:
    """One proposed term, kept when it keeps the limits. The caller tries again when it is not."""
    if s.carry == "none" and op in "+-":
        # Without a carry the second number is drawn from digits that cannot carry: far fewer
        # blind draws would make one, and a chain needs two.
        pair = None
        a = pick(rng, s.a, 0, s.max)
        ranges = None if a is None else calm(s.b, a, op)
        if a is not None and ranges is not None:
            room = top - a if op == "+" else a
            b = pick(rng, ranges, 0, min(room, s.max))
            pair = None if b is None else (a, b)
    else:
        pair = propose(s, op, top, rng)
    return pair if pair is not None and valid(s, op, *pair, top) else None


def left_pair(s: Settings, op: str, op2: str, top: int, rng: random.Random) -> dict | None:
    """`a op b op2 c`, with `a op b` worked out first."""
    # Times mostly take a small third factor first, so the first pair has the rest of the top.
    small = None
    if op2 == "*" and rng.random() < s.lean:
        small = pick(rng, s.c, 2, min(s.max, max(2, isqrt(top))))
    if op2 == "/":
        # The divisor is drawn first, so the first pair can be aimed at a multiple of it.
        c = pick(rng, s.c, 2, min(s.max, max(2, isqrt(top)))) if rng.random() < s.lean else None
        school_way = c is not None
        if c is None:
            c = pick(rng, s.c, 1, s.max)
        if c is None:
            return None
        hi = top // (2 * c) if op == "/" else top // c
        q = rng.randint(2, hi) if school_way and hi >= 2 else rng.randint(0, top // c)
        pair = aimed(s, op, c * q, top, rng)
        if pair is None:
            return None
        v = result(op, *pair)
    elif small is not None:
        pair = once(s, op, top // small, rng)
        if pair is None:
            return None
        v = result(op, *pair)
        c = small
    else:
        pair = once(s, op, top, rng)
        if pair is None:
            return None
        v = result(op, *pair)
        room = {"+": top - v, "-": v, "*": top // v if v else s.max}[op2]
        ranges = s.c
        if s.carry == "none" and op2 in "+-":
            ranges = calm(s.c, v, op2)
            if ranges is None:
                return None
        c = pick(rng, ranges, 0, min(room, s.max))
        if c is None:
            return None
    return {
        "op": op,
        "a": pair[0],
        "b": pair[1],
        "op2": op2,
        "c": c,
        "result": result(op2, v, c),
        "rest": 0,
    }


def right_pair(s: Settings, op: str, op2: str, top: int, rng: random.Random) -> dict | None:
    """`a op (b op2 c)`, with `b op2 c` worked out first."""
    # Times mostly take a small first factor, so the inner pair has the rest of the top.
    small = None
    if op == "*" and rng.random() < s.lean:
        small = pick(rng, s.a, 2, min(s.max, max(2, isqrt(top))))
    inner = s.model_copy(update={"a": s.b, "b": s.c})
    pair = once(inner, op2, top if small is None else top // small, rng)
    if pair is None:
        return None
    b, c = pair
    w = result(op2, b, c)
    if op == "+":
        ranges = calm(s.a, w, "+") if s.carry == "none" else s.a
        a = None if ranges is None else pick(rng, ranges, 0, min(top - w, s.max))
    elif op == "-":
        ranges = calm(s.a, w, "-", first=True) if s.carry == "none" else s.a
        a = None if ranges is None else pick(rng, ranges, w, s.max)
    elif op == "*":
        if small is None:
            small = pick(rng, s.a, 0, s.max if w == 0 else min(top // w, s.max))
        a = small
    else:
        # A multiple of w divides by w with no remainder; it must also have the digits of a.
        if w and s.max // w >= 2 and rng.random() < s.lean:
            a = rng.randint(2, s.max // w) * w
        else:
            a = rng.randint(0, s.max // w) * w if w else None
        if a is not None and not fits(s.a, a):
            return None
    if a is None:
        return None
    return {"op": op, "a": a, "b": b, "op2": op2, "c": c, "result": result(op, a, w), "rest": 0}


def dull(s: Settings, e: dict, found: dict) -> bool:
    """Whether a three-number task is too plain for a block with a Punkt sign: two of its numbers
    are 0 or 1, its bracket comes to 0 or 1, or its result is 0 or 1 once the block has its
    share."""
    if sum(e[k] in (0, 1) for k in "abc") > 1:
        return True
    if "paren" in e:
        inner = (
            result(e["op"], e["a"], e["b"])
            if e["paren"] == "left"
            else result(e["op2"], e["b"], e["c"])
        )
        if inner in (0, 1):
            return True
    # A result of 0 or 1 is rare: the block holds at most its tenth part of them, both together.
    return (
        e["result"] in (0, 1)
        and sum(t["result"] in (0, 1) for t in found.values()) >= s.count // 10
    )


def take(
    s: Settings, top: int, shape: tuple, rng: random.Random, found: dict, strict: bool = False
) -> bool:
    """Draws one task of a shape, and keeps it when it is sound and not yet there. A strict
    draw also refuses a dull task."""
    ops1, ops2, build, paren = shape
    e = build(s, rng.choice(ops1), rng.choice(ops2), top, rng)
    if e is None:
        return False
    if paren:
        e["paren"] = paren
    if not sound(s, e, top):
        return False
    if strict and dull(s, e, found):
        return False
    key = (e["a"], e["op"], e["b"], e["op2"], e["c"], e.get("paren"))
    if key in found:
        return False
    only = bound(s)
    if only and not any(told(s, e, k) for k in only):
        return False
    found[key] = e
    return True


def draw_shape(
    s: Settings,
    top: int,
    shape: tuple,
    want: int,
    rng: random.Random,
    found: dict,
    strict: bool = False,
) -> None:
    """Draws up to `want` new tasks of a shape. A shape that brings nothing new 200 times in a
    row has no more to give: tight limits leave few tasks, and the tries would all be spent."""
    got = idle = 0
    for _ in range(300 + 20 * s.count):
        if got == want or idle == 200:
            break
        new = take(s, top, shape, rng, found, strict)
        got += new
        idle = 0 if new else idle + 1


def chains(s: Settings, top: int) -> list[dict]:
    """The three-number exercises: each shape gets its share, and the others fill any gap."""
    s = s.model_copy(update={"rest": False})
    rng = random.Random(s.seed)
    ops = list(dict.fromkeys(s.ops))
    strich = [op for op in ops if op in "+-"]
    punkt = [op for op in ops if op in "*/"]
    # Without the switch a task has one kind of operation: all Strich or all Punkt.
    shapes: list[tuple] = [(group, group, left_pair, None) for group in (strich, punkt) if group]
    if s.pvs and strich and punkt:
        # Punkt first and Punkt last; with brackets, the Strich part in brackets too. A plain shape
        # and one with brackets take turns, so even two tasks have brackets in one of them.
        plain = [(punkt, strich, left_pair, None), (strich, punkt, right_pair, None)]
        round_strich = [(strich, punkt, left_pair, "left"), (punkt, strich, right_pair, "right")]
        shapes = (
            [x for pair in zip(plain, round_strich, strict=True) for x in pair]
            if s.brackets
            else plain
        )
    # A dict keeps the order they were found in, so a seed gives the same tasks again.
    found: dict[tuple, dict] = {}
    k = len(shapes)
    shares = [s.count // k + (i < s.count % k) for i in range(k)]
    if punkt:
        # Each shape keeps its share. Its school tasks come first; about one task in ten is left
        # to the old way, which also fills a shape where school tasks are few.
        school = s.model_copy(update={"lean": 1.0})
        s = s.model_copy(update={"lean": 0.0})
        few = s.count // 10
        # The draws are strict: a dull task waits for the last fill, where tight limits take it.
        for i, shape in enumerate(shapes):
            before = len(found)
            draw_shape(
                school, top, shape, shares[i] - few // k - (i < few % k), rng, found, strict=True
            )
            draw_shape(s, top, shape, shares[i] - (len(found) - before), rng, found, strict=True)
    else:
        for share, shape in zip(shares, shapes, strict=True):
            draw_shape(s, top, shape, share, rng, found)
    # With a Punkt sign the fill first refuses dull tasks, and only then takes any.
    for strict in (True, False) if punkt else (False,):
        for shape in shapes:
            draw_shape(s, top, shape, s.count - len(found), rng, found, strict)
    out = list(found.values())
    if len(shapes) > 1:
        rng.shuffle(out)
    return out


def run(op: str, x: int, y: int) -> int | None:
    """One step as a pupil works it out: None for a division by nothing or with a remainder."""
    if op == "/":
        return x // y if y and x % y == 0 else None
    return {"+": x + y, "-": x - y, "*": x * y}[op]


def comes_to(e: dict, nums: dict[str, int]) -> int | None:
    """What a three-number task comes to with these numbers, worked out as the task says."""
    op, op2 = e["op"], e["op2"]
    right = e["paren"] == "right" if "paren" in e else op2 in "*/" and op in "+-"
    if right:
        w = run(op2, nums["b"], nums["c"])
        return None if w is None else run(op, nums["a"], w)
    v = run(op, nums["a"], nums["b"])
    return None if v is None else run(op2, v, nums["c"])


def told(s: Settings, e: dict, k: str) -> bool:
    """Whether the hidden number k is the only one that makes the task come out at its result.
    Above 1000 only 0 and the neighbours of the true number are tried, to keep it quick."""
    nums = {"a": e["a"], "b": e["b"], "c": e["c"]}
    true = nums[k]
    near = sorted({0, true - 1, true, true + 1})
    tries = range(s.max + 1) if s.max <= 1000 else [x for x in near if 0 <= x <= s.max]
    # A second number that fits settles it: a block whose digits leave only open gaps asks this
    # of every task it tries, and most of those have a fit at every turn.
    fit = 0
    for x in tries:
        fit += comes_to(e, {**nums, k: x}) == e["result"]
        if fit > 1:
            return False
    return fit == 1


def chained(s: Settings) -> dict:
    """The three-number exercises, and the limits that stand in the way of more."""
    found = chains(s, s.max)
    if s.format == "gap":
        # A gap is only fair when the result tells which number is hidden: one draw per task.
        hide = random.Random(s.seed)
        allowed = gaps_of(s)
        for e in found:
            fair = [k for k in "abc" if told(s, e, k)]
            # No number is told: hide the result, as any number would fit a hidden a, b or c.
            cands = [k for k in allowed if k == "result" or k in fair] or fair or ["result"]
            k = hide.choice(cands)
            if k != "result":
                e["hide"] = k
    if len(found) == s.count:
        return {"exercises": found, "loosen": None}
    table = loosened(s)
    names = ("carry", "a", "b", "c", "max", "brackets", "zero", "one", "distinct")
    loosen = [name for name in names if len(chains(*table[name])) > len(found)]
    return {"exercises": found, "loosen": loosen}
