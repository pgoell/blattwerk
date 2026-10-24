"""The exercises for one block of settings."""

import random

from fastapi import APIRouter

from blattwerk.auth import Teacher
from blattwerk.maths.chains import chained
from blattwerk.maths.compare import compared
from blattwerk.maths.model import Settings, gaps_of, loosened, places, scaled, three
from blattwerk.maths.pairs import groups, kin, loose
from blattwerk.maths.written import written

router = APIRouter(prefix="/api")


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
    # With three numbers the switch counts for nothing: they are drawn the same either way.
    if three(s):
        s = s.model_copy(update={"small": False})
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
    names = ("carry", "rest", "a", "b", "max", "family", "zero", "one", "distinct", "small")
    loosen = [name for name in names if len(groups(*table[name])) > len(drawn)]
    return {"exercises": exercises, "loosen": loosen}


@router.post("/maths")
def maths(body: Settings, user: Teacher) -> dict:
    return generate(body)
