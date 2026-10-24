"""The written method on squared paper: one cell per character."""

from blattwerk.maths.model import ANSWER, CARRY, GIVEN, SIGNS
from blattwerk.maths.pairs import carries


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
