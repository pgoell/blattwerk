"""Whether a plus or minus task crosses a place (#838).

Plus crosses a place when the two digits there sum to more than 10. A sum of 10
(7 + 3, 17 + 23) does not, and nothing is carried on to the next place. Minus
crosses a place when that digit of the first number is smaller than the second's,
so the digit would go below 0.

The three rules are the Zehner, the Hunderter and the Tausender, smallest place
first. A place counts once the Zahlenraum goes past it: past 10, past 100, past
1000. With places after the comma the list starts at the smallest of those.
"none" at the top place that counts also rules out every place above it.
"""

from typing import Literal

Rule = Literal["none", "required", "either"]
Carry = tuple[Rule, Rule, Rule]
NAMES = ("zehner", "hunderter", "tausender", "einer", "zehntel")
_BELOW = ("einer", "zehntel")
_RULES = ("none", "required", "either")


def coerce_carry(value: object) -> Carry:
    """Three rules. An older switch: "none" is all three, "required" the smallest, "either" none."""
    if isinstance(value, str):
        if value not in _RULES:
            raise ValueError("carry")
        if value == "none":
            return ("none", "none", "none")
        if value == "required":
            return ("required", "either", "either")
        return ("either", "either", "either")
    if (
        isinstance(value, (list, tuple))
        and len(value) == 3
        and all(item in _RULES for item in value)
    ):
        return (value[0], value[1], value[2])
    raise ValueError("carry")


def crosses_at(op: str, a: int, b: int, place: int) -> bool:
    """Whether place `place` (0 the Einer) crosses."""
    da = a // 10**place % 10
    db = b // 10**place % 10
    if op == "+":
        return da + db > 10
    return da < db


def offered(max_n: int) -> int:
    """How many of the three places the Zahlenraum reaches, from the smallest."""
    n, bound = 0, 10
    while n < 3 and max_n > bound:
        n += 1
        bound *= 10
    return n


def keeps(carry: object, max_n: int, op: str, a: int, b: int) -> bool:
    """Whether a plus or minus pair keeps the place rules. Other operations do."""
    if op not in "+-":
        return True
    rules = coerce_carry(carry)
    n = offered(max_n)
    for i in range(n):
        if rules[i] != "either" and crosses_at(op, a, b, i) != (rules[i] == "required"):
            return False
    if n and rules[n - 1] == "none":
        for i in range(n, max(len(str(abs(a))), len(str(abs(b))))):
            if crosses_at(op, a, b, i):
                return False
    return True


def all_none(carry: object, max_n: int) -> bool:
    """Whether every place that counts is "none", so a draw can avoid them."""
    rules = coerce_carry(carry)
    n = offered(max_n)
    return n > 0 and all(rules[i] == "none" for i in range(n))


def rule_name(index: int, decimals: int) -> str:
    """The loosen name of place `index` with `decimals` places after the comma."""
    place = index - decimals
    if place >= 0:
        return ("zehner", "hunderter", "tausender")[place]
    return _BELOW[-place - 1]


def variants(carry: object, max_n: int, decimals: int) -> dict[str, Carry]:
    """Each binding place set to "either": the name, and the rules with that one loosened."""
    rules = list(coerce_carry(carry))
    n = offered(max_n)
    out: dict[str, Carry] = {}
    for i in range(n):
        if rules[i] == "either":
            continue
        nxt = rules.copy()
        nxt[i] = "either"
        out[rule_name(i, decimals)] = (nxt[0], nxt[1], nxt[2])
    return out
