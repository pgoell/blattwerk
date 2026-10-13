"""The maths generator: exercises within exact limits, and their written working."""

import json
import random
from collections import Counter
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
    if op == "/" and b == 0:
        return False
    # A written task with a 0 as a number teaches nothing, whatever the operation.
    if s.format == "written" and 0 in (a, b):
        return False
    if not s.zero and (0 in (a, b) or (op == "-" and a == b) or (op == "/" and a < b)):
        return False
    if not s.one and ((op == "*" and 1 in (a, b)) or (op == "/" and b == 1)):
        return False
    if s.distinct and a == b:
        return False
    only = [] if three(s) else bound(s)
    if only and all(loose(op, a, b, k) for k in only):
        return False
    if op in "+-":
        if s.carry != "either" and (s.carry == "required") != any(carries(op, a, b)):
            return False
        return a + b <= top if op == "+" else b <= a
    if op == "*":
        return a * b <= top
    return b > 0 and (s.rest is None or s.rest == (a % b > 0))


def school(op: str, a: int, b: int) -> bool:
    """Whether a times or divide task is one a school sets: no 0 and no 1 as a factor,
    a divisor or a quotient."""
    if op == "*":
        return a >= 2 and b >= 2
    if op == "/":
        return b >= 2 and a // b >= 2
    return True


def smaller(op: str, a: int, b: int) -> int:
    """The smaller factor of a times task; of a divide task, the smaller of divisor and quotient."""
    return min(a, b) if op == "*" else min(b, a // b)


def weighted(
    op: str, pairs: list[tuple[int, int]], n: int, rng: random.Random
) -> list[tuple[int, int]]:
    """`n` of the pairs, each smaller factor as likely as the next."""
    keys = Counter(smaller(op, *p) for p in pairs)
    # A pair ranks by u ** (pairs sharing its key), so each key gets the same total chance.
    return sorted(pairs, key=lambda p: rng.random() ** keys[smaller(op, *p)], reverse=True)[:n]


def school_pair(s: Settings, op: str, top: int, rng: random.Random) -> tuple[int, int] | None:
    """A times or divide task of school size: one number is small and the other is drawn to fit."""
    if op == "*":
        a_small = rng.random() < 0.5
        small_r, other_r = (s.a, s.b) if a_small else (s.b, s.a)
        small = pick(rng, small_r, 2, min(s.max, max(2, isqrt(top))))
        if small is None:
            return None
        other = pick(rng, other_r, 2, min(top // small, s.max))
        if other is None:
            return None
        return (small, other) if a_small else (other, small)
    if rng.random() < 0.5:
        b = pick(rng, s.b, 2, min(s.max, max(2, isqrt(s.max))))
        if b is None or s.max // b < 2:
            return None
        q = rng.randint(2, s.max // b)
    else:
        q = rng.randint(2, max(2, min(s.max, isqrt(s.max))))
        b = pick(rng, s.b, 2, s.max // q)
        if b is None:
            return None
    return q * b + (0 if s.rest is False else rng.randrange(b)), b


def propose(s: Settings, op: str, top: int, rng: random.Random) -> tuple[int, int] | None:
    """Two numbers likely to make an exercise: the second is drawn from what the first leaves."""
    if op in "*/" and rng.random() < s.lean:
        pair = school_pair(s, op, top, rng)
        if pair is not None:
            return pair
    # A written task has no 0 as a number, so its draws start at 1.
    low = 1 if s.format == "written" else 0
    if op == "/":
        b = pick(rng, s.b, 1, s.max)
        if b is None:
            return None
        return rng.randint(low, s.max // b) * b + (0 if s.rest is False else rng.randrange(b)), b
    a = pick(rng, s.a, low, s.max)
    if a is None:
        return None
    room = {"+": top - a, "-": a, "*": top // a if a else s.max}[op]
    b = pick(rng, s.b, low, min(room, s.max))
    return None if b is None else (a, b)


def loose(op: str, a: int, b: int, k: str) -> bool:
    """Whether any number fits a gap at k, so the gap is no task."""
    if k == "a":
        return op == "*" and b == 0
    if k == "b":
        return (op == "*" and a == 0) or (op == "/" and a // b == 0)
    return False


def bound(s: Settings) -> list[str]:
    """The numbers a gap must hide one of: the ticked ones, when the teacher set them and left the
    result out."""
    if s.format != "gap" or s.gaps is None:
        return []
    allowed = gaps_of(s)
    return [] if "result" in allowed else allowed


def valid_pairs(s: Settings, op: str, top: int) -> list[tuple[int, int]]:
    """Every pair of numbers that keeps the limits for one operation."""
    # Only these limits tell whether a pair is valid; a row and a gap take the same pairs.
    limits = s.model_dump_json(
        include={"max", "a", "b", "carry", "rest", "zero", "one", "distinct"}
    )
    only = tuple([] if three(s) else bound(s))
    return list(kept(limits, s.format == "written", only, op, top))


# A block is rolled anew and changed many times within the same limits, and a Zahlenraum of 100
# has ten thousand pairs to try, so the last answers are remembered; the cap bounds memory.
@lru_cache(maxsize=32)
def kept(
    limits: str, on_paper: bool, only: tuple[str, ...], op: str, top: int
) -> tuple[tuple[int, int], ...]:
    """`valid_pairs` for the limits as JSON, remembered."""
    fields = json.loads(limits)
    # The digit ranges come back as lists; they must be tuples to be remembered by `below`.
    fields["a"] = [tuple(r) for r in fields["a"]]
    fields["b"] = [tuple(r) for r in fields["b"]]
    fields["format"] = "written" if on_paper else "row"
    if only:
        fields.update(format="gap", gaps=list(only))
    # The pairs do not hang on the signs, the count or the seed: any will do here. The settings
    # are not checked again, as a big Zahlenraum may have been widened past its limit.
    s = Settings.model_construct(ops=["+"], count=1, seed=0, **fields)
    bs = [nth(s.b, i) for i in range(below(s.b, s.max))]
    return tuple(
        (a, b)
        for a in (nth(s.a, i) for i in range(below(s.a, s.max)))
        for b in bs
        if valid(s, op, a, b, top)
    )


def draw(s: Settings, op: str, count: int, top: int, rng: random.Random) -> list[tuple[int, int]]:
    """Up to `count` different exercises of one operation."""
    sizes = below(s.a, s.max), below(s.b, s.max)
    if not all(sizes):
        return []
    if sizes[0] * sizes[1] <= SMALL:
        every = valid_pairs(s, op, top)
        if op in "+-":
            return rng.sample(every, min(count, len(every)))
        # About one task in ten may be a plain one with a 0 or a 1; the rest are school tasks.
        school_pairs = [p for p in every if school(op, *p)]
        others = [p for p in every if not school(op, *p)]
        n_others = min(count // 10, len(others))
        n_school = min(count - n_others, len(school_pairs))
        n_others = min(count - n_school, len(others))
        out = weighted(op, school_pairs, n_school, rng) + rng.sample(others, n_others)
        rng.shuffle(out)
        return out
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


REVERSE = {"+": "-", "-": "+", "*": "/", "/": "*"}


def kin(s: Settings) -> str:
    """The family that holds for these settings: "none" when the tasks have none."""
    if s.family == "none" or s.format not in ("row", "gap") or three(s):
        return "none"
    if s.family == "swap" and not {"+", "*"} & set(s.ops):
        return "none"
    return s.family


def relatives(s: Settings, op: str, a: int, b: int) -> list[tuple[str, int, int]]:
    """The tasks of the family that holds the task (op, a, b), the task itself first."""
    kind = kin(s)
    if kind == "swap":
        return [(op, a, b), (op, b, a)] if a != b else []
    if kind == "reverse":
        return [(op, a, b), (REVERSE[op], result(op, a, b), b)]
    if op == "/" and s.moves == "a":
        return [(op, a, b), (op, a - b, b), (op, a + b, b)]
    if op == "/":
        q, r = divmod(a, b)
        return [(op, a, b), (op, q * (b - 1) + r, b - 1), (op, q * (b + 1) + r, b + 1)]
    if s.moves == "a":
        return [(op, a, b), (op, a - 1, b), (op, a + 1, b)]
    return [(op, a, b), (op, a, b - 1), (op, a, b + 1)]


def family_of(s: Settings, op: str, a: int, b: int, top: int) -> list[tuple[str, int, int]] | None:
    """The family of a valid task when every task of it keeps the limits, else None."""
    if not valid(s, op, a, b, top):
        return None
    members = relatives(s, op, a, b)
    if not members or any(x < 0 or y < 0 or not valid(s, m, x, y, top) for m, x, y in members):
        return None
    return members


def take_family(
    s: Settings,
    op: str,
    a: int,
    b: int,
    top: int,
    found: dict[frozenset, list],
    tasks: set[tuple[str, int, int]],
    repeat: bool,
) -> bool:
    """Keeps the family of the task when its key is new, and unless `repeat`, none of its tasks
    is in the block yet."""
    fam = family_of(s, op, a, b, top)
    if fam is None or frozenset(fam) in found or (not repeat and not tasks.isdisjoint(fam)):
        return False
    found[frozenset(fam)] = fam
    tasks.update(fam)
    return True


def fill_small(
    s: Settings,
    op: str,
    top: int,
    want: int,
    found: dict[frozenset, list],
    tasks: set[tuple[str, int, int]],
    rng: random.Random,
) -> None:
    """Families of one operation from every pair that keeps the limits. New tasks come first:
    a repeat is taken only where the share is short."""
    cand = valid_pairs(s, op, top)
    if op in "+-":
        rng.shuffle(cand)
    else:
        # The school tasks come first, as in draw().
        school_pairs = [p for p in cand if school(op, *p)]
        others = [p for p in cand if not school(op, *p)]
        rng.shuffle(others)
        cand = weighted(op, school_pairs, len(school_pairs), rng) + others
    got = 0
    for repeat in (False, True):
        for a, b in cand:
            if got == want:
                return
            got += take_family(s, op, a, b, top, found, tasks, repeat)


def fill_big(
    s: Settings,
    op: str,
    top: int,
    want: int,
    found: dict[frozenset, list],
    tasks: set[tuple[str, int, int]],
    rng: random.Random,
) -> None:
    """Families of one operation from proposed pairs, each with only new tasks."""
    got = 0
    for _ in range(1000 + 50 * want):
        if got == want:
            break
        pair = propose(s, op, top, rng)
        if pair is not None:
            got += take_family(s, op, *pair, top, found, tasks, False)


def families(s: Settings, top: int) -> list[list[tuple[str, int, int]]]:
    """The families of the block, each as its tasks. The count is shared among the operations."""
    if kin(s) == "reverse":
        s = s.model_copy(update={"rest": False})
    rng = random.Random(s.seed)
    ops = list(dict.fromkeys(s.ops))
    if kin(s) == "swap":
        ops = [op for op in ops if op in "+*"]
    found: dict[frozenset, list] = {}
    tasks: set[tuple[str, int, int]] = set()
    sizes = below(s.a, s.max), below(s.b, s.max)
    if not all(sizes):
        return []
    for i, op in enumerate(ops):
        want = s.count // len(ops) + (i < s.count % len(ops))
        fill = fill_small if sizes[0] * sizes[1] <= SMALL else fill_big
        fill(s, op, top, want, found, tasks, rng)
    out = list(found.values())
    if len(ops) > 1:
        rng.shuffle(out)
    return out


def groups(s: Settings, top: int) -> list[list[tuple[str, int, int]]]:
    """The drawn tasks by family. Without a family each task stands alone."""
    if kin(s) == "none":
        return [[task] for task in pairs(s, top)]
    return families(s, top)


def result(op: str, a: int, b: int) -> int:
    """What a term comes to."""
    return a // b if op == "/" else {"+": a + b, "-": a - b, "*": a * b}[op]


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
    # Two plain numbers that must differ have no equal sides.
    if s.distinct and s.sides == "nn":
        n_equal = 0
    out = draw_comparisons(s, ops, top, n_equal, 500 + 50 * n_equal, True, rng)
    out += draw_comparisons(s, ops, top, s.count - n_equal, 1000 + 50 * s.count, False, rng)
    rng.shuffle(out)
    return out


def put(cells: list[list], right: int, y: int, text: str, kind: int = GIVEN) -> None:
    """Writes one character a cell, the last one in column `right`."""
    cells += [[right - i, y, ch, kind] for i, ch in enumerate(reversed(text))]


def written(op: str, a: int, b: int, d: int = 0, money: bool = False) -> dict:
    """The written method on squared paper: the cells with a character, and the ruled lines.

    A cell is [column, row, character, kind], a line [from column, to column, above row, kind].
    """
    cells: list[list] = []
    lines: list[list] = []
    sa, sb = str(a), str(b)
    if op in "+-":

        def digits(n: int) -> str:
            """A number with its comma and exactly d places after it."""
            return f"{n // 10**d},{n % 10**d:0{d}d}" if d else str(n)

        result = a + b if op == "+" else a - b
        right = len(digits(max(a, result)))
        put(cells, right, 0, digits(a))
        put(cells, right, 1, digits(b))
        cells.append([0, 1, SIGNS[op], GIVEN])
        for i, carry in enumerate(carries(op, a, b)):
            if carry:
                # The column of place i + 1: a comma takes one column after the d places.
                j = i + 1
                cells.append([right - j - (d > 0 and j >= d), 2, "1", CARRY])
        put(cells, right, 3, digits(result), ANSWER)
        if money:
            cells += [[right + 1, y, "€", GIVEN] for y in (0, 1, 3)]
        end = right + 2 if money else right + 1
        lines.append([0, end, 3, GIVEN])
        return {"cols": end, "rows": 4, "cells": cells, "lines": lines}
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
        "family": (s.model_copy(update={"family": "none"}), s.max),
        "zero": (s.model_copy(update={"zero": True}), s.max),
        "one": (s.model_copy(update={"one": True}), s.max),
        "distinct": (s.model_copy(update={"distinct": False}), s.max),
    }


def compared(s: Settings) -> dict:
    """The comparisons for these settings, and the limits that stand in the way of more."""
    found = compare(s, s.max)
    if len(found) == s.count:
        return {"exercises": found, "loosen": None}
    table = loosened(s)
    names = ("carry", "a", "b", "max", "close", "equal", "zero", "one", "distinct")
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
    are 0 or 1, its bracket comes to 0 or 1, or its result is 0 once the block has its share."""
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
    # A result of 0 is rare: the block holds at most its tenth part of them.
    return e["result"] == 0 and sum(t["result"] == 0 for t in found.values()) >= s.count // 10


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


def gaps_of(s: Settings) -> list[str]:
    """What a gap may hide, in the fixed order a, b, c, result."""
    shown = ("a", "b", "c", "result") if three(s) else ("a", "b", "result")
    ticked = s.gaps or ["a", "b", "c"]
    return [k for k in shown if k in ticked] or [k for k in shown if k != "result"]


def exercise_of(s: Settings, op: str, a: int, b: int, d: int, rng: random.Random) -> dict:
    """One two-number exercise: its result, its rest, the number a gap hides and its grid."""
    result, rest = divmod(a, b) if op == "/" else ({"+": a + b, "-": a - b, "*": a * b}[op], 0)
    exercise: dict = {"op": op, "a": a, "b": b, "result": result, "rest": rest}
    if s.format == "gap":
        allowed = gaps_of(s)
        hide = rng.choice(allowed)
        # With a 0 that makes any number fit the gap, that number is not hidden: another one is.
        if loose(op, a, b, hide):
            hide = next(k for k in [*allowed, "a", "b", "result"] if not loose(op, a, b, k))
        if hide != "result":
            exercise["hide"] = hide
    if s.format == "written":
        exercise["grid"] = written(op, a, b, d, s.money and d > 0)
    return exercise


def generate(s: Settings) -> dict:
    """The exercises for these settings. With fewer than asked for, `loosen` names the limits
    that stand in the way: without one of them there would be more."""
    d = places(s)
    s = scaled(s)
    if s.format == "compare":
        return compared(s)
    if three(s):
        return chained(s)
    rng = random.Random(s.seed)
    drawn = groups(s, s.max)
    exercises = []
    for n, family in enumerate(drawn):
        for op, a, b in family:
            exercise = exercise_of(s, op, a, b, d, rng)
            if kin(s) != "none":
                exercise["family"] = n
            exercises.append(exercise)
    if len(drawn) == s.count:
        return {"exercises": exercises, "loosen": None}
    table = loosened(s)
    names = ("carry", "rest", "a", "b", "max", "family", "zero", "one", "distinct")
    loosen = [name for name in names if len(groups(*table[name])) > len(drawn)]
    return {"exercises": exercises, "loosen": loosen}


@router.post("/maths")
def maths(body: Settings, user: User) -> dict:
    return generate(body)
