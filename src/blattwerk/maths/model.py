"""Settings of a maths block, and the counts and limits the generator shares."""

import random
from functools import lru_cache
from math import prod
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

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
    # Nachkommastellen: the numbers have this many places after the comma, for plus and minus only.
    decimals: Literal[0, 1, 2] = 0
    # Geld: two places after the comma, always.
    money: bool = False
    # The digits of the places after the comma, Zehntel first, for each of the three numbers.
    af: list[Range] = []
    bf: list[Range] = []
    cf: list[Range] = []
    # How often a times or divide task is drawn the school way; the generator alone sets it.
    lean: float = 0.9
    # Aufgabenfamilien: each drawn task comes with its swap, its reverse or its two neighbours.
    family: Literal["none", "swap", "reverse", "neighbour"] = "none"
    # Which number moves in a Nachbaraufgabe.
    moves: Literal["a", "b"] = "a"
    # Lücke: what a gap may hide. None is every number of the task and never the result.
    gaps: Annotated[list[Literal["a", "b", "c", "result"]], Field(min_length=1)] | None = None
    # Aufgaben mit 0: off keeps 0 out as a number and as a result.
    zero: bool = True
    # Aufgaben mit 1 beim Malnehmen und Teilen: off keeps 1 out as a factor and as a divisor.
    one: bool = True
    # Keine gleichen Zahlen: on keeps tasks out whose numbers are equal.
    distinct: bool = False
    # Kleines Einmaleins: both factors of a times task, and the divisor and the quotient of a divide
    # task, lie from 1 to 10.
    small: bool = False

    @model_validator(mode="after")
    def places_fit(self) -> Settings:
        if any(lo > hi for lo, hi in self.a + self.b + self.c + self.af + self.bf + self.cf):
            raise ValueError("a place's lowest digit lies above its highest")
        n = len(str(self.max))
        self.a = (self.a + [(0, 9)] * n)[:n]
        self.b = (self.b + [(0, 9)] * n)[:n]
        self.c = (self.c + [(0, 9)] * n)[:n]
        self.af = (self.af + [(0, 9)] * 2)[:2]
        self.bf = (self.bf + [(0, 9)] * 2)[:2]
        self.cf = (self.cf + [(0, 9)] * 2)[:2]
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


def three(s: Settings) -> bool:
    """Whether the exercises have three numbers. Only the row and the gap format take them."""
    return s.numbers == 3 and s.format in ("row", "gap")


def gaps_of(s: Settings) -> list[str]:
    """What a gap may hide, in the fixed order a, b, c, result."""
    shown = ("a", "b", "c", "result") if three(s) else ("a", "b", "result")
    ticked = s.gaps or ["a", "b", "c"]
    return [k for k in shown if k in ticked] or [k for k in shown if k != "result"]


def places(s: Settings) -> int:
    """Places after the comma. Only plus and minus take any; a comparison takes none."""
    if s.format == "compare" or any(op in "*/" for op in s.ops):
        return 0
    return 2 if s.money else s.decimals


def scaled(s: Settings) -> Settings:
    """The settings in whole numbers of the smallest place: 3,50 is 350."""
    d = places(s)
    if not d:
        return s
    return s.model_copy(
        update={
            "max": s.max * 10**d,
            "a": [*reversed(s.af[:d]), *s.a],
            "b": [*reversed(s.bf[:d]), *s.b],
            "c": [*reversed(s.cf[:d]), *s.c],
        }
    )


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
        "family": (s.model_copy(update={"family": "none"}), s.max),
        "zero": (s.model_copy(update={"zero": True}), s.max),
        "one": (s.model_copy(update={"one": True}), s.max),
        "distinct": (s.model_copy(update={"distinct": False}), s.max),
        "small": (s.model_copy(update={"small": False}), s.max),
    }


def plain(s: Settings, e: dict) -> bool:
    """Whether a three-number exercise keeps the switches: no 0 or 1 where they keep it out,
    and no equal numbers."""
    nums = (e["a"], e["b"], e["c"])
    if not s.zero and (0 in nums or e["result"] == 0):
        return False
    if s.distinct and len(set(nums)) < 3:
        return False
    if s.one:
        return True
    right = e["paren"] == "right" if "paren" in e else e["op2"] in "*/" and e["op"] in "+-"
    # The written operands of each sign: a and b for the first, b and c for the second.
    of_op = [e["a"]] + ([] if right else [e["b"]])
    of_op2 = [e["c"]] + ([e["b"]] if right else [])
    if (e["op"] == "*" and 1 in of_op) or (e["op2"] == "*" and 1 in of_op2):
        return False
    return not ((e["op"] == "/" and not right and e["b"] == 1) or (e["op2"] == "/" and e["c"] == 1))
