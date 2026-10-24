"""Comparisons: two sides, and how close they lie."""

import random
from math import isqrt

from blattwerk.maths.model import CLOSE, Settings, fits, loosened, pick
from blattwerk.maths.pairs import propose, result, valid


def term_side(op: str, a: int, b: int) -> dict:
    """A term as one side of a comparison, with its result."""
    return {"op": op, "a": a, "b": b, "value": result(op, a, b)}


def term(s: Settings, op: str, top: int, rng: random.Random) -> tuple[int, int] | None:
    """A term of this operation that keeps every limit, from up to 20 tries."""
    for i in range(20):
        if i == 2 and op in "*/":
            # Where the digits leave no school task, the school way is given up: it costs two
            # draws a try.
            s = s.model_copy(update={"lean": 0.0})
        pair = propose(s, op, top, rng)
        if pair is not None and valid(s, op, *pair, top):
            return pair
    return None


def aimed(
    s: Settings, op: str, target: int, top: int, rng: random.Random
) -> tuple[int, int] | None:
    """A term of this operation whose result is `target`, or None."""
    pair: tuple[int, int] | None = None
    if op == "+":
        a = pick(rng, s.a, 0, min(target, s.max))
        pair = None if a is None else (a, target - a)
    elif op == "-":
        b = pick(rng, s.b, 0, s.max - target)
        pair = None if b is None else (target + b, b)
    elif op == "*":
        if target == 0:
            a = pick(rng, s.a, 0, s.max)
            pair = None if a is None else (a, 0)
        else:
            ways = [(d, target // d) for d in range(1, isqrt(target) + 1) if target % d == 0]
            ways = list(dict.fromkeys(ways + [(b, a) for a, b in ways]))
            ways = [(a, b) for a, b in ways if fits(s.a, a) and fits(s.b, b)]
            plain = [w for w in ways if min(w) >= 2] if ways and rng.random() < s.lean else []
            pair = rng.choice(plain or ways) if ways else None
    else:
        b = pick(rng, s.b, 2, s.max // max(target, 1)) if rng.random() < s.lean else None
        if b is None:
            b = pick(rng, s.b, 1, s.max // max(target, 1))
        pair = None if b is None else (target * b, b)
    return pair if pair is not None and valid(s, op, *pair, top) else None


def term_of(s: Settings, ops: list[str], top: int, rng: random.Random) -> dict | None:
    """A term of a random operation, its limits kept."""
    op = rng.choice(ops)
    pair = term(s, op, top, rng)
    return None if pair is None else term_side(op, *pair)


def aimed_term(
    s: Settings, ops: list[str], target: int, top: int, rng: random.Random
) -> dict | None:
    """A term of a random operation that comes to `target`."""
    op = rng.choice(ops)
    pair = aimed(s, op, target, top, rng)
    return None if pair is None else term_side(op, *pair)


def free_side(s: Settings, ops: list[str], top: int, rng: random.Random) -> dict | None:
    """The right side when no result is aimed at: any number, or any term."""
    low = 0 if s.zero else 1
    if s.sides == "nn":
        n = pick(rng, s.b, low, s.max)
        return None if n is None else {"value": n}
    if s.sides == "tn":
        return {"value": rng.randint(low, s.max)}
    return term_of(s, ops, top, rng)


def aimed_side(
    s: Settings, ops: list[str], target: int, top: int, rng: random.Random
) -> dict | None:
    """The right side when it must come to `target`: the number itself, or a term that does."""
    if s.sides == "nn":
        return {"value": target} if fits(s.b, target) and target <= s.max else None
    if s.sides == "tn":
        return {"value": target} if target <= s.max else None
    return aimed_term(s, ops, target, top, rng)


def comparison(
    s: Settings, ops: list[str], top: int, equal_one: bool, rng: random.Random
) -> dict | None:
    """One comparison whose sides keep every limit, or None when this try fails."""
    low = 0 if s.zero else 1
    if s.sides == "nn":
        n = pick(rng, s.a, low, s.max)
        left = None if n is None else {"value": n}
    else:
        left = term_of(s, ops, top, rng)
    if left is None:
        return None
    if equal_one or s.close:
        target = left["value"]
        if not equal_one:
            target += rng.choice(CLOSE)
            if not low <= target <= (top if s.sides == "tt" else s.max):
                return None
        right = aimed_side(s, ops, target, top, rng)
    else:
        right = free_side(s, ops, top, rng)
    if right is None or (right["value"] == left["value"]) != equal_one:
        return None
    # A term never stands against itself: `3 + 4 ○ 3 + 4` is no task.
    if left == right and "op" in left:
        return None
    lo, hi = left["value"], right["value"]
    return {"left": left, "right": right, "sign": "=" if lo == hi else "<" if lo < hi else ">"}


def draw_comparisons(
    s: Settings,
    ops: list[str],
    top: int,
    want: int,
    tries: int,
    equal_one: bool,
    rng: random.Random,
) -> list[dict]:
    """Up to `want` different comparisons, all with equal sides or all with unequal ones.

    A draw that brings nothing new 200 times in a row has no more to give: tight limits leave
    few comparisons, and the rest of the tries would all be spent.
    """
    # A dict keeps the order they were found in, so a seed gives the same comparisons again.
    found: dict[tuple, dict] = {}
    idle = 0
    for _ in range(tries):
        if len(found) == want or idle == 200:
            break
        e = comparison(s, ops, top, equal_one, rng)
        if e is not None:
            key = (tuple(e["left"].items()), tuple(e["right"].items()))
            if key not in found:
                found[key] = e
                idle = 0
                continue
        idle += 1
    return list(found.values())


def compare(s: Settings, top: int) -> list[dict]:
    """The comparisons, `equal` of them with equal sides and the rest with unequal ones."""
    # A term has no remainder here: a division comes out even, whatever `rest` says.
    s = s.model_copy(update={"rest": False})
    rng = random.Random(s.seed)
    ops: list[str] = list(dict.fromkeys(s.ops))
    # The "=" tasks are made first, so a short supply of them is not filled with others.
    n_equal = (2 * s.count + 5) // 10 if s.equal == "some" else 0
    # Two plain numbers that must differ have no equal sides.
    if s.distinct and s.sides == "nn":
        n_equal = 0
    out = draw_comparisons(s, ops, top, n_equal, 500 + 50 * n_equal, True, rng)
    out += draw_comparisons(s, ops, top, s.count - n_equal, 1000 + 50 * s.count, False, rng)
    rng.shuffle(out)
    return out


def compared(s: Settings) -> dict:
    """The comparisons for these settings, and the limits that stand in the way of more."""
    found = compare(s, s.max)
    if len(found) == s.count:
        return {"exercises": found, "loosen": None}
    table = loosened(s)
    names = ("carry", "a", "b", "max", "close", "equal", "zero", "one", "distinct", "small")
    # A limit already at its loosest changes nothing, so it is not tried again.
    return {
        "exercises": found,
        "loosen": [
            name
            for name in names
            if table[name] != (s, s.max) and len(compare(*table[name])) > len(found)
        ],
    }
