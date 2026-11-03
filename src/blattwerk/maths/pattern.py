"""Patterns for the numbers of a maths task.

A pattern is written as the number is written, the highest place first. `X` is any digit and a
digit is that digit. The length is the number of digits, so `X0` is 10, 20, ... and never 0.
The leading digit of a longer pattern is never 0. "Die Null darf vorkommen" is off when a 0 in
the written number is refused, including a 0 the pattern itself asks for.
"""

from blattwerk.maths.model import Range, Settings, three


def allow(s: Settings, op: str) -> bool:
    """Whether the digit 0 may occur for this operation's family."""
    if op in "+-":
        return s.nil.get("strich", True)
    return s.nil.get("punkt", True)


def matches(pattern: str, n: int, allow_zero: bool) -> bool:
    """Whether `n` is the pattern. An empty pattern only applies the zero switch."""
    if n < 0:
        return False
    text = str(n)
    if not allow_zero and "0" in text:
        return False
    if not pattern:
        return True
    if len(text) != len(pattern):
        return False
    return all(ch == "X" or ch == digit for ch, digit in zip(pattern, text, strict=True))


def cut(ranges: list[Range], pattern: str, allow_zero: bool) -> list[Range] | None:
    """`ranges` narrowed to the pattern, units first. None when no number fits.

    An empty pattern leaves the ranges alone: the zero switch is checked on the number.
    """
    if not pattern:
        return list(ranges)
    width, length = len(ranges), len(pattern)
    if length > width:
        return None
    out: list[Range] = []
    for i in range(width):
        lo, hi = ranges[i]
        if i >= length:
            lo, hi = max(lo, 0), min(hi, 0)
        else:
            ch = pattern[length - 1 - i]
            if ch == "X":
                lead = i == length - 1 and length > 1
                lo, hi = max(lo, 1 if lead or not allow_zero else 0), min(hi, 9)
            else:
                digit = int(ch)
                if digit == 0 and (not allow_zero or (i == length - 1 and length > 1)):
                    return None
                lo, hi = max(lo, digit), min(hi, digit)
        if lo > hi:
            return None
        out.append((lo, hi))
    return out


def for_op(s: Settings, op: str) -> Settings:
    """Settings whose digit ranges are the pattern and whose zero switch is this operation's."""
    zero_ok = allow(s, op)
    a = cut(list(s.a), s.pa, zero_ok)
    b = cut(list(s.b), s.pb, zero_ok)
    if a is None or b is None:
        data = s.model_dump()
        data["a"] = [(1, 0)]
        data["b"] = [(1, 0)]
        return Settings.model_construct(**data)
    if a == list(s.a) and b == list(s.b):
        return s
    return s.model_copy(update={"a": a, "b": b})


def operands(s: Settings, op: str, a: int, b: int) -> bool:
    """Whether both numbers keep the pattern and the zero switch of `op`."""
    zero_ok = allow(s, op)
    return matches(s.pa, a, zero_ok) and matches(s.pb, b, zero_ok)


def result_ok(s: Settings, op: str, result: int) -> bool:
    """Whether the result keeps its pattern. A chain checks the result on the whole task."""
    if three(s):
        return True
    pattern = "" if s.format == "compare" else s.pr
    return matches(pattern, result, allow(s, op))


def plain_zero(s: Settings, ops: list[str]) -> bool:
    """Whether a bare number, which belongs to every selected operation, may contain a 0."""
    return all(allow(s, op) for op in ops)
