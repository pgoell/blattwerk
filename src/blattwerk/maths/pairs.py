"""Which pairs of numbers a block may draw, and the families those pairs make."""

import json
import random
from collections import Counter
from functools import lru_cache
from math import isqrt

from blattwerk.maths.model import (
    SMALL,
    Settings,
    below,
    fits,
    gaps_of,
    nth,
    pick,
    three,
)


def carries(op: str, a: int, b: int) -> list[int]:
    """What each place of a sum or a difference carries to the next, units first."""
    out, carry = [], 0
    while a or b:
        carry = int(a % 10 + b % 10 + carry > 9 if op == "+" else a % 10 - carry < b % 10)
        out.append(carry)
        a, b = a // 10, b // 10
    return out


def kleine(op: str, a: int, b: int, low: int = 1) -> bool:
    """Whether a times or divide task is of the kleine Einmaleins: its factors, or its divisor and
    its quotient, lie from `low` to 10."""
    if op == "*":
        return low <= a <= 10 and low <= b <= 10
    return low <= b <= 10 and low <= a // b <= 10


def valid(s: Settings, op: str, a: int, b: int, top: int) -> bool:
    """Whether an exercise keeps every limit. `top` is the highest result."""
    if not (fits(s.a, a) and fits(s.b, b) and a <= s.max and b <= s.max):
        return False
    if op == "/" and b == 0:
        return False
    # The kleine Einmaleins has no 0 in it, so the switch keeps 0 out of these tasks. Without the
    # tasks with 1 its rows start at 2, so a quotient of 1 is out as well.
    if s.small and op in "*/" and not kleine(op, a, b, 1 if s.one else 2):
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
        include={"max", "a", "b", "carry", "rest", "zero", "one", "distinct", "small"}
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


def small_pairs(s: Settings, op: str, top: int) -> list[tuple[int, int]]:
    """Every kleine Einmaleins pair that keeps the limits. A big Zahlenraum draws too rarely
    from its own pairs to find these, so they are tried one by one."""
    if op == "*":
        cands = [(a, b) for a in range(1, 11) for b in range(1, 11)]
    else:
        cands = [
            (q * b + r, b)
            for q in range(1, 11)
            for b in range(1, 11)
            for r in ([0] if s.rest is False else (range(1, b) if s.rest else range(b)))
        ]
    return [p for p in cands if valid(s, op, *p, top)]


def chosen(op: str, every: list[tuple[int, int]], count: int, rng: random.Random):
    """Up to `count` of the pairs of a times or divide task."""
    # About one task in ten may be a plain one with a 0 or a 1; the rest are school tasks.
    school_pairs = [p for p in every if school(op, *p)]
    others = [p for p in every if not school(op, *p)]
    n_others = min(count // 10, len(others))
    n_school = min(count - n_others, len(school_pairs))
    n_others = min(count - n_school, len(others))
    out = weighted(op, school_pairs, n_school, rng) + rng.sample(others, n_others)
    rng.shuffle(out)
    return out


def draw(s: Settings, op: str, count: int, top: int, rng: random.Random) -> list[tuple[int, int]]:
    """Up to `count` different exercises of one operation."""
    sizes = below(s.a, s.max), below(s.b, s.max)
    if not all(sizes):
        return []
    if sizes[0] * sizes[1] <= SMALL:
        every = valid_pairs(s, op, top)
        if op in "+-":
            return rng.sample(every, min(count, len(every)))
        return chosen(op, every, count, rng)
    if s.small and op in "*/":
        return chosen(op, small_pairs(s, op, top), count, rng)
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
) -> bool:
    """Keeps the family of the task when none of its tasks is in the block yet, so a block
    never holds a task twice."""
    fam = family_of(s, op, a, b, top)
    if fam is None or frozenset(fam) in found or not tasks.isdisjoint(fam):
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
    """Families of one operation from every pair that keeps the limits. The school tasks come
    first; plain families (a * or / that is no school task) are at most a tenth of the block."""
    cand = valid_pairs(s, op, top)
    if op in "+-":
        rng.shuffle(cand)
    else:
        # The school tasks come first, as in draw().
        school_pairs = [p for p in cand if school(op, *p)]
        others = [p for p in cand if not school(op, *p)]
        rng.shuffle(others)
        cand = weighted(op, school_pairs, len(school_pairs), rng) + others
    got, few = 0, want // 10
    for a, b in cand:
        if got == want:
            return
        plain = op in "*/" and not school(op, a, b)
        if plain and not few:
            continue
        if take_family(s, op, a, b, top, found, tasks):
            got += 1
            few -= plain


def fill_big(
    s: Settings,
    op: str,
    top: int,
    want: int,
    found: dict[frozenset, list],
    tasks: set[tuple[str, int, int]],
    rng: random.Random,
) -> None:
    """Families of one operation from proposed pairs, each with only new tasks. Plain families
    are at most a tenth of the block, as in fill_small."""
    got, few = 0, want // 10
    for _ in range(1000 + 50 * want):
        if got == want:
            break
        pair = propose(s, op, top, rng)
        if pair is None:
            continue
        plain = op in "*/" and not school(op, *pair)
        if plain and not few:
            continue
        if take_family(s, op, *pair, top, found, tasks):
            got += 1
            few -= plain


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
