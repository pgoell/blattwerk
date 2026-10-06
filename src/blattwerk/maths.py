"""The maths generator: exercises within exact limits, and their written working."""

import random
from math import prod
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


class Settings(BaseModel):
    ops: Annotated[list[Op], Field(min_length=1)]
    # The Zahlenraum: no number and no result lies above it.
    max: Annotated[int, Field(ge=1, le=1_000_000)]
    # The digits each number may have, units first. A place left out takes any digit.
    a: list[Range] = []
    b: list[Range] = []
    carry: Literal["none", "required", "either"] = "either"
    # Whether a division leaves a remainder. None takes both; only the generator asks for that.
    rest: bool | None = False
    format: Literal["row", "gap", "written"] = "row"
    count: Annotated[int, Field(ge=1, le=100)]
    seed: int

    @model_validator(mode="after")
    def places_fit(self) -> Settings:
        if any(lo > hi for lo, hi in self.a + self.b):
            raise ValueError("a place's lowest digit lies above its highest")
        n = len(str(self.max))
        self.a = (self.a + [(0, 9)] * n)[:n]
        self.b = (self.b + [(0, 9)] * n)[:n]
        return self


def below(ranges: list[Range], bound: int) -> int:
    """How many numbers with each digit in its range are at most `bound`."""
    if bound < 0:
        return 0
    if not ranges:
        return 1
    *rest, (lo, hi) = ranges
    top, low = divmod(bound, 10 ** len(rest))
    lower = max(0, min(hi, top - 1) - lo + 1) * prod(most - least + 1 for least, most in rest)
    return lower + (below(rest, low) if lo <= top <= hi else 0)


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


def generate(s: Settings) -> dict:
    """The exercises for these settings. With fewer than asked for, `loosen` names the limits
    that stand in the way: without one of them there would be more."""
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
    free = [(0, 9)] * len(s.a)
    looser = {
        "carry": (s.model_copy(update={"carry": "either"}), s.max),
        "rest": (s.model_copy(update={"rest": None}), s.max),
        "a": (s.model_copy(update={"a": free}), s.max),
        "b": (s.model_copy(update={"b": free}), s.max),
        "max": (s, s.max * 10),
    }
    loosen = [name for name, (to, top) in looser.items() if len(pairs(to, top)) > len(found)]
    return {"exercises": exercises, "loosen": loosen}


@router.post("/maths")
def maths(body: Settings, user: User) -> dict:
    return generate(body)
