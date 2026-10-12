"""The maths generator: exercises within exact limits, and their written working."""

import random
from functools import lru_cache
from math import isqrt, prod
from typing import Annotated, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from blattwerk.auth import User

router = APIRouter(prefix="/api")

Op = Literal["+", "-", "*", "/"]
Digit = Annotated[int, Field(ge=0, le=9)]
# The lowest and the highest digit a place may hold.
Range = tuple[Digit, Digit]
# The signs as German schools write them, with a true minus sign.
SIGNS = {"+": "+", "-": "\u2212", "*": "·", "/": ":"}
# Cells of a written exercise: printed on the sheet, filled in by the answer key, or a small carry.
GIVEN, ANSWER, CARRY = 0, 1, 2
# With no more pairs of numbers than this, every pair is tried, so no exercise is missed.
SMALL = 20_000
# Knapp: how far apart the sides of a close comparison lie, in units or in tens.
CLOSE = [-20, -10, -2, -1, 1, 2, 10, 20]


class Settings(BaseModel):
    ops: Annotated[list[Op], Field(min_length=1)]
    # The Zahlenraum: no number and no result lies above it.
    max: Annotated[int, Field(ge=1, le=1_000_000)]
    # The digits each number may have, units first. A place left out takes any digit.
    a: list[Range] = []
    b: list[Range] = []
    # The digits of the third number, for the exercises of three numbers.
    c: list[Range] = []
    carry: Literal["none", "required", "either"] = "either"
    # Whether a division leaves a remainder. None takes both; only the generator asks for that.
    rest: bool | None = False
    format: Literal["row", "gap", "written", "compare"] = "row"
    # What stands on each side of a comparison: number and number, term and number, term and term.
    sides: Literal["nn", "tn", "tt"] = "tn"
    # Knapp: the sides of a comparison differ by 1 or 2 units or tens.
    close: bool = False
    # Whether some comparisons, about one in five, have equal sides.
    equal: Literal["none", "some"] = "some"
    count: Annotated[int, Field(ge=1, le=100)]
    seed: int
    # Zahlen pro Aufgabe: two numbers, or three for the row and the gap format.
    numbers: Literal[2, 3] = 2
    # Punkt vor Strich: a * or / task with a + or - task, the * or / worked out first.
    pvs: bool = False
    # Mit Klammern: about half of the tasks with brackets round the Strich part.
    brackets: bool = False

    @model_validator(mode="after")
    def places_fit(self) -> Settings:
        if any(lo > hi for lo, hi in self.a + self.b + self.c):
            raise ValueError("a place's lowest digit lies above its highest")
        n = len(str(self.max))
        self.a = (self.a + [(0, 9)] * n)[:n]
        self.b = (self.b + [(0, 9)] * n)[:n]
        self.c = (self.c + [(0, 9)] * n)[:n]
        return self


def below(ranges: list[Range], bound: int) -> int:
    """How many numbers with each digit in its range are at most `bound`."""
    return counted(tuple(ranges), bound)


# A comparison asks the same counts over and over, so they are remembered; the cap bounds memory.
@lru_cache(maxsize=4096)
def counted(ranges: tuple[Range, ...], bound: int) -> int:
    """`below` for a tuple of ranges, remembered."""
    if bound < 0:
        return 0
    if not ranges:
        return 1
    rest, (lo, hi) = ranges[:-1], ranges[-1]
    top, low = divmod(bound, 10 ** len(rest))
    lower = max(0, min(hi, top - 1) - lo + 1) * prod(most - least + 1 for least, most in rest)
    return lower + (counted(rest, low) if lo <= top <= hi else 0)


def nth(ranges: list[Range], k: int) -> int:
    """The number at place `k` when all numbers with such digits stand in rising order."""
    n = 0
    for i, (lo, hi) in enumerate(ranges):
        k, digit = divmod(k, hi - lo + 1)
        n += (lo + digit) * 10**i
    return n


def pick(rng: random.Random, ranges: list[Range], lo: int, hi: int) -> int | None:
    """A number with such digits from `lo` to `hi`, each as likely as the next."""
    first, end = below(ranges, lo - 1), below(ranges, hi)
    return nth(ranges, rng.randrange(first, end)) if first < end else None


def fits(ranges: list[Range], n: int) -> bool:
    return n < 10 ** len(ranges) and all(
        lo <= n // 10**i % 10 <= hi for i, (lo, hi) in enumerate(ranges)
    )


def carries(op: str, a: int, b: int) -> list[int]:
    """What each place of a sum or a difference carries to the next, units first."""
    out, carry = [], 0
    while a or b:
        carry = int(a % 10 + b % 10 + carry > 9 if op == "+" else a % 10 - carry < b % 10)
        out.append(carry)
        a, b = a // 10, b // 10
    return out


def valid(s: Settings, op: str, a: int, b: int, top: int) -> bool:
    """Whether an exercise keeps every limit. `top` is the highest result."""
    if not (fits(s.a, a) and fits(s.b, b) and a <= s.max and b <= s.max):
        return False
    if op in "+-":
        if s.carry != "either" and (s.carry == "required") != any(carries(op, a, b)):
            return False
        return a + b <= top if op == "+" else b <= a
    if op == "*":
        return a * b <= top
    return b > 0 and (s.rest is None or s.rest == (a % b > 0))


def propose(s: Settings, op: str, top: int, rng: random.Random) -> tuple[int, int] | None:
    """Two numbers likely to make an exercise: the second is drawn from what the first leaves."""
    if op == "/":
        b = pick(rng, s.b, 1, s.max)
        if b is None:
            return None
        return rng.randint(0, s.max // b) * b + (0 if s.rest is False else rng.randrange(b)), b
    a = pick(rng, s.a, 0, s.max)
    if a is None:
        return None
    room = {"+": top - a, "-": a, "*": top // a if a else s.max}[op]
    b = pick(rng, s.b, 0, min(room, s.max))
    return None if b is None else (a, b)


def draw(s: Settings, op: str, count: int, top: int, rng: random.Random) -> list[tuple[int, int]]:
    """Up to `count` different exercises of one operation."""
    sizes = below(s.a, s.max), below(s.b, s.max)
    if not all(sizes):
        return []
    if sizes[0] * sizes[1] <= SMALL:
        bs = [nth(s.b, i) for i in range(sizes[1])]
        every = [
            (a, b)
            for a in (nth(s.a, i) for i in range(sizes[0]))
            for b in bs
            if valid(s, op, a, b, top)
        ]
        return rng.sample(every, min(count, len(every)))
    # A dict keeps the order they were found in, so a seed gives the same exercises again.
    found: dict[tuple[int, int], None] = {}
    for _ in range(1000 + 50 * count):
        if len(found) == count:
            break
        pair = propose(s, op, top, rng)
        if pair and valid(s, op, *pair, top):
            found[pair] = None
    return list(found)


def pairs(s: Settings, top: int) -> list[tuple[str, int, int]]:
    """The exercises, shared evenly among the operations and then mixed."""
    rng = random.Random(s.seed)
    ops = list(dict.fromkeys(s.ops))
    out: list[tuple[str, int, int]] = [
        (op, a, b)
        for i, op in enumerate(ops)
        for a, b in draw(s, op, s.count // len(ops) + (i < s.count % len(ops)), top, rng)
    ]
    if len(ops) > 1:
        rng.shuffle(out)
    return out


def result(op: str, a: int, b: int) -> int:
    """What a term comes to."""
    return a // b if op == "/" else {"+": a + b, "-": a - b, "*": a * b}[op]


def term_side(op: str, a: int, b: int) -> dict:
    """A term as one side of a comparison, with its result."""
    return {"op": op, "a": a, "b": b, "value": result(op, a, b)}


def term(s: Settings, op: str, top: int, rng: random.Random) -> tuple[int, int] | None:
    """A term of this operation that keeps every limit, from up to 20 tries."""
    for _ in range(20):
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
            pair = rng.choice(ways) if ways else None
    else:
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
    if s.sides == "nn":
        n = pick(rng, s.b, 0, s.max)
        return None if n is None else {"value": n}
    if s.sides == "tn":
        return {"value": rng.randint(0, s.max)}
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
    if s.sides == "nn":
        n = pick(rng, s.a, 0, s.max)
        left = None if n is None else {"value": n}
    else:
        left = term_of(s, ops, top, rng)
    if left is None:
        return None
    if equal_one or s.close:
        target = left["value"]
        if not equal_one:
            target += rng.choice(CLOSE)
            if not 0 <= target <= (top if s.sides == "tt" else s.max):
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
    """Up to `want` different comparisons, all with equal sides or all with unequal ones."""
    # A dict keeps the order they were found in, so a seed gives the same comparisons again.
    found: dict[tuple, dict] = {}
    for _ in range(tries):
        if len(found) == want:
            break
        e = comparison(s, ops, top, equal_one, rng)
        if e is not None:
            found.setdefault((tuple(e["left"].items()), tuple(e["right"].items())), e)
    return list(found.values())


def compare(s: Settings, top: int) -> list[dict]:
    """The comparisons, `equal` of them with equal sides and the rest with unequal ones."""
    # A term has no remainder here: a division comes out even, whatever `rest` says.
    s = s.model_copy(update={"rest": False})
    rng = random.Random(s.seed)
    ops: list[str] = list(dict.fromkeys(s.ops))
    # The "=" tasks are made first, so a short supply of them is not filled with others.
    n_equal = (2 * s.count + 5) // 10 if s.equal == "some" else 0
    out = draw_comparisons(s, ops, top, n_equal, 500 + 50 * n_equal, True, rng)
    out += draw_comparisons(s, ops, top, s.count - n_equal, 1000 + 50 * s.count, False, rng)
    rng.shuffle(out)
    return out


def put(cells: list[list], right: int, y: int, text: str, kind: int = GIVEN) -> None:
    """Writes one character a cell, the last one in column `right`."""
    cells += [[right - i, y, ch, kind] for i, ch in enumerate(reversed(text))]


def written(op: str, a: int, b: int) -> dict:
    """The written method on squared paper: the cells with a character, and the ruled lines.

    A cell is [column, row, character, kind], a line [from column, to column, above row, kind].
    """
    cells: list[list] = []
    lines: list[list] = []
    sa, sb = str(a), str(b)
    if op in "+-":
        result = a + b if op == "+" else a - b
        right = len(str(max(a, result)))
        put(cells, right, 0, sa)
        put(cells, right, 1, sb)
        cells.append([0, 1, SIGNS[op], GIVEN])
        for i, carry in enumerate(carries(op, a, b)):
            if carry:
                cells.append([right - i - 1, 2, "1", CARRY])
        lines.append([0, right + 1, 3, GIVEN])
        put(cells, right, 3, str(result), ANSWER)
        return {"cols": right + 1, "rows": 4, "cells": cells, "lines": lines}
    if op == "*":
        right = len(sa) + len(sb)
        put(cells, right, 0, sa + SIGNS[op] + sb)
        lines.append([0, right + 1, 1, GIVEN])
        if len(sb) == 1:
            put(cells, right, 1, str(a * b), ANSWER)
            return {"cols": right + 1, "rows": 2, "cells": cells, "lines": lines}
        # Each part of the product ends below the digit it was multiplied by.
        parts = [a * int(digit) * 10 ** (len(sb) - 1 - j) for j, digit in enumerate(sb)]
        for j, digit in enumerate(sb):
            put(cells, len(sa) + 1 + j, 1 + j, str(a * int(digit)), ANSWER)
        y = 1 + len(sb)
        carry = 0
        for i in range(len(str(a * b)) - 1):
            carry = (sum(part // 10**i % 10 for part in parts) + carry) // 10
            if carry:
                cells.append([right - i - 1, y, str(carry), CARRY])
        lines.append([0, right + 1, y + 1, GIVEN])
        put(cells, right, y + 1, str(a * b), ANSWER)
        return {"cols": right + 1, "rows": y + 2, "cells": cells, "lines": lines}
    # Division. Column 0 is kept for the minus signs of the working.
    quotient, rest = divmod(a, b)
    head = f"{sa}{SIGNS[op]}{sb}="
    put(cells, len(head), 0, head)
    answer = str(quotient) + (f"R{rest}" if rest else "")
    put(cells, len(head) + len(answer), 0, answer, ANSWER)
    # The first part of the dividend is as short as the divisor goes into.
    i = next((i for i in range(len(sa)) if int(sa[: i + 1]) >= b), len(sa) - 1)
    part = sa[: i + 1]
    y = 1
    while True:
        col = 1 + i
        under = str(int(part) // b * b)
        left = int(part) - int(under)
        put(cells, col, y, under, ANSWER)
        cells.append([col - len(under), y, SIGNS["-"], ANSWER])
        lines.append([col + 1 - max(len(part), len(under)), col + 1, y + 1, ANSWER])
        i += 1
        if i == len(sa):
            put(cells, col, y + 1, str(left), ANSWER)
            break
        # What is left goes down a row, with the next digit of the dividend behind it.
        part = f"{left}{sa[i]}"
        put(cells, col + 1, y + 1, part, ANSWER)
        y += 2
    return {"cols": len(head) + len(answer) + 1, "rows": y + 2, "cells": cells, "lines": lines}


def loosened(s: Settings) -> dict[str, tuple[Settings, int]]:
    """Each limit taken off in turn: the settings with it looser, and the highest result."""
    free = [(0, 9)] * len(s.a)
    return {
        "carry": (s.model_copy(update={"carry": "either"}), s.max),
        "rest": (s.model_copy(update={"rest": None}), s.max),
        "a": (s.model_copy(update={"a": free}), s.max),
        "b": (s.model_copy(update={"b": free}), s.max),
        "c": (s.model_copy(update={"c": [(0, 9)] * len(s.c)}), s.max),
        "brackets": (s.model_copy(update={"brackets": False}), s.max),
        "max": (s, s.max * 10),
        "close": (s.model_copy(update={"close": False}), s.max),
        "equal": (s.model_copy(update={"equal": "none"}), s.max),
    }


def compared(s: Settings) -> dict:
    """The comparisons for these settings, and the limits that stand in the way of more."""
    found = compare(s, s.max)
    if len(found) == s.count:
        return {"exercises": found, "loosen": None}
    table = loosened(s)
    names = ("carry", "a", "b", "max", "close", "equal")
    # A limit already at its loosest changes nothing, so it is not tried again.
    return {
        "exercises": found,
        "loosen": [
            name
            for name in names
            if table[name] != (s, s.max) and len(compare(*table[name])) > len(found)
        ],
    }


def three(s: Settings) -> bool:
    """Whether the exercises have three numbers. Only the row and the gap format take them."""
    return s.numbers == 3 and s.format in ("row", "gap")


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
    return fit and inside and worked(s, e, top) == e["result"]


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
    if op2 == "/":
        # The divisor is drawn first, so the first pair can be aimed at a multiple of it.
        c = pick(rng, s.c, 1, s.max)
        if c is None:
            return None
        pair = aimed(s, op, c * rng.randint(0, top // c), top, rng)
        if pair is None:
            return None
        v = result(op, *pair)
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
    pair = once(s.model_copy(update={"a": s.b, "b": s.c}), op2, top, rng)
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
        a = pick(rng, s.a, 0, s.max if w == 0 else min(top // w, s.max))
    else:
        # A multiple of w divides by w with no remainder; it must also have the digits of a.
        a = rng.randint(0, s.max // w) * w if w else None
        if a is not None and not fits(s.a, a):
            return None
    if a is None:
        return None
    return {"op": op, "a": a, "b": b, "op2": op2, "c": c, "result": result(op, a, w), "rest": 0}


def take(s: Settings, top: int, shape: tuple, rng: random.Random, found: dict) -> bool:
    """Draws one task of a shape, and keeps it when it is sound and not yet there."""
    ops1, ops2, build, paren = shape
    e = build(s, rng.choice(ops1), rng.choice(ops2), top, rng)
    if e is None:
        return False
    if paren:
        e["paren"] = paren
    if not sound(s, e, top):
        return False
    key = (e["a"], e["op"], e["b"], e["op2"], e["c"], e.get("paren"))
    if key in found:
        return False
    found[key] = e
    return True


def draw_shape(
    s: Settings, top: int, shape: tuple, want: int, rng: random.Random, found: dict
) -> None:
    """Draws up to `want` new tasks of a shape. A shape that brings nothing new 200 times in a
    row has no more to give: tight limits leave few tasks, and the tries would all be spent."""
    got = idle = 0
    for _ in range(300 + 20 * s.count):
        if got == want or idle == 200:
            break
        new = take(s, top, shape, rng, found)
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
    for i, shape in enumerate(shapes):
        draw_shape(s, top, shape, s.count // len(shapes) + (i < s.count % len(shapes)), rng, found)
    for shape in shapes:
        draw_shape(s, top, shape, s.count - len(found), rng, found)
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
    return sum(comes_to(e, {**nums, k: x}) == e["result"] for x in tries) == 1


def chained(s: Settings) -> dict:
    """The three-number exercises, and the limits that stand in the way of more."""
    found = chains(s, s.max)
    if s.format == "gap":
        # A gap is only fair when the result tells which number is hidden: one draw per task.
        hide = random.Random(s.seed)
        for e in found:
            e["hide"] = hide.choice([k for k in "abc" if told(s, e, k)] or "abc")
    if len(found) == s.count:
        return {"exercises": found, "loosen": None}
    table = loosened(s)
    names = ("carry", "a", "b", "c", "max", "brackets")
    loosen = [name for name in names if len(chains(*table[name])) > len(found)]
    return {"exercises": found, "loosen": loosen}


def generate(s: Settings) -> dict:
    """The exercises for these settings. With fewer than asked for, `loosen` names the limits
    that stand in the way: without one of them there would be more."""
    if s.format == "compare":
        return compared(s)
    if three(s):
        return chained(s)
    found = pairs(s, s.max)
    rng = random.Random(s.seed)
    exercises = []
    for op, a, b in found:
        result, rest = divmod(a, b) if op == "/" else ({"+": a + b, "-": a - b, "*": a * b}[op], 0)
        exercise: dict = {"op": op, "a": a, "b": b, "result": result, "rest": rest}
        if s.format == "gap":
            exercise["hide"] = rng.choice("ab")
        if s.format == "written":
            exercise["grid"] = written(op, a, b)
        exercises.append(exercise)
    if len(found) == s.count:
        return {"exercises": exercises, "loosen": None}
    table = loosened(s)
    names = ("carry", "rest", "a", "b", "max")
    loosen = [name for name in names if len(pairs(*table[name])) > len(found)]
    return {"exercises": exercises, "loosen": loosen}


@router.post("/maths")
def maths(body: Settings, user: User) -> dict:
    return generate(body)
