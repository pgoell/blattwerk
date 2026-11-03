"""The written method on squared paper: one cell per character."""

from blattwerk.maths.model import ANSWER, CARRY, GIVEN, HEADER, SIGNS
from blattwerk.maths.pairs import carries

# Place letters, the smallest place first. Decimals use the small letters, tenths first.
WHOLE = ("E", "Z", "H", "T", "ZT", "HT", "M")
FRACTION = ("z", "h")


def put(cells: list[list], right: int, y: int, text: str, kind: int = GIVEN) -> None:
    """Writes one character a cell, the last one in column `right`."""
    cells += [[right - i, y, ch, kind] for i, ch in enumerate(reversed(text))]


def column(right: int, place: int, decimals: int) -> int:
    """The column of a place, units first. The comma takes the column after the decimals."""
    return right - place - (decimals > 0 and place >= decimals)


def digits_of(n: int, decimals: int) -> str:
    """A number with its comma and exactly `decimals` places after it."""
    if not decimals:
        return str(n)
    return f"{n // 10**decimals},{n % 10**decimals:0{decimals}d}"


def sum_carries(nums: list[int]) -> list[int]:
    """What each place of a sum carries to the next, units first."""
    out, carry, rest = [], 0, list(nums)
    while any(rest):
        carry = (sum(n % 10 for n in rest) + carry) // 10
        out.append(carry)
        rest = [n // 10 for n in rest]
    return out


def unbundle(a: int, b: int) -> dict[int, str]:
    """The small digits Entbündeln writes above the minuend, by place, units first.

    A place that receives a ten shows 1. A place that only lends shows what is left
    of it. The places between, which were 0, show 9.
    """
    width = max(len(str(a)), len(str(b)), 1)
    ad = [a // 10**i % 10 for i in range(width)]
    bd = [b // 10**i % 10 for i in range(width)]
    marks: dict[int, str] = {}
    for i in range(width):
        if ad[i] >= bd[i]:
            continue
        j = next((j for j in range(i + 1, width) if ad[j] > 0), None)
        if j is None:
            break
        ad[j] -= 1
        marks[j] = str(ad[j])
        for k in range(j - 1, i, -1):
            ad[k] = 9
            marks[k] = "9"
        marks[i] = "1"
        ad[i] += 10
    return marks


def letter(place: int, decimals: int) -> str | None:
    """The Stellenwert of a place, or None past the names we have."""
    if place < decimals:
        index = decimals - 1 - place
        return FRACTION[index] if index < len(FRACTION) else None
    index = place - decimals
    return WHOLE[index] if index < len(WHOLE) else None


def header(right: int, decimals: int, y: int) -> list[list]:
    """One letter over each digit column."""
    cells: list[list] = []
    place = 0
    while True:
        col = column(right, place, decimals)
        if col < 1:
            break
        name = letter(place, decimals)
        if name:
            cells.append([col, y, name, HEADER])
        place += 1
    return cells


def column_calc(
    op: str,
    a: int,
    b: int,
    decimals: int,
    money: bool,
    extra: tuple[int, ...],
    minus: str,
    stellen: bool,
    signs: str,
) -> dict:
    """A plus or a minus on squared paper, including a sum of more than two numbers."""
    nums = [a, b, *extra] if op == "+" else [a, b]
    result = sum(nums) if op == "+" else a - b
    right = len(digits_of(max(*nums, result), decimals))
    cells: list[list] = []
    y = 0
    if stellen:
        cells += header(right, decimals, y)
        y += 1
    mark_row = None
    if op == "-" and minus in ("unbundle", "extend"):
        mark_row = y
        y += 1
    number_rows = []
    for i, n in enumerate(nums):
        number_rows.append(y)
        put(cells, right, y, digits_of(n, decimals))
        if i and (signs == "all" or i == len(nums) - 1):
            cells.append([0, y, SIGNS[op], GIVEN])
        y += 1
    if op == "-" and minus == "unbundle" and mark_row is not None:
        for place, ch in unbundle(a, b).items():
            cells.append([column(right, place, decimals), mark_row, ch, CARRY])
    else:
        carried = sum_carries(nums) if op == "+" else carries("-", a, b)
        for i, carry in enumerate(carried):
            if carry:
                cells.append([column(right, i + 1, decimals), y, str(carry), CARRY])
        if op == "-" and minus == "extend" and mark_row is not None:
            for i, carry in enumerate(carries("-", a, b)):
                if carry:
                    cells.append([column(right, i, decimals), mark_row, "1", CARRY])
        y += 1
    end = right + 2 if money else right + 1
    lines = [[0, end, y, GIVEN]]
    put(cells, right, y, digits_of(result, decimals), ANSWER)
    if money:
        for row in (*number_rows, y):
            cells.append([right + 1, row, "€", GIVEN])
    return {"cols": end, "rows": y + 1, "cells": cells, "lines": lines}


def written(
    op: str,
    a: int,
    b: int,
    d: int = 0,
    money: bool = False,
    *,
    extra: tuple[int, ...] = (),
    minus: str = "fill",
    stellen: bool = False,
    signs: str = "all",
) -> dict:
    """The written method on squared paper: the cells with a character, and the ruled lines.

    A cell is [column, row, character, kind], a line [from column, to column, above row, kind].
    `minus` draws a subtraction: "fill" Ergänzen, "unbundle" Entbündeln, "extend" Erweitern.
    `stellen` writes the place letters over a plus or a minus. `signs` is "all" or "last".
    `extra` stacks more numbers under a plus.
    """
    cells: list[list] = []
    lines: list[list] = []
    sa, sb = str(a), str(b)
    if op in "+-":
        return column_calc(op, a, b, d, money, extra, minus, stellen, signs)
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
