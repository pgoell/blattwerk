"""Schriftlich: the three minus methods, the Stellenwerte, and a plus of more than two numbers.

The small carry of each minus method sits where that method is taught. A plus of three or four
numbers is one column, with a sign on every row or only on the last. The first number keeps its
pattern and each following number keeps the second. Übertrag none draws no carry.
"""

from playwright.sync_api import expect
from ui import at, box, maths, user

from blattwerk.maths import CARRY, GIVEN, HEADER, Settings, generate, written


def text(grid, kinds=(0, 1, 2, 3)):
    """A written exercise as lines of text: dashes for a ruled line, a tilde for a minus sign."""
    rows = [[" "] * grid["cols"] for _ in range(grid["rows"])]
    for x, y, ch, kind in grid["cells"]:
        assert rows[y][x] == " ", "two characters in one cell"
        if kind in kinds:
            rows[y][x] = ch
    out = []
    for y, row in enumerate(rows):
        for x1, x2, above, kind in grid["lines"]:
            if above == y and kind in kinds:
                out.append((" " * x1 + "-" * (x2 - x1)).rstrip())
        out.append("".join(row).rstrip())
    return "\n".join(out).replace("\u2212", "~")


def carries_of(nums):
    """What each place of a sum carries, units first."""
    out, carry, rest = [], 0, list(nums)
    while any(rest):
        carry = (sum(n % 10 for n in rest) + carry) // 10
        out.append(carry)
        rest = [n // 10 for n in rest]
    return out


def test_abziehverfahren_puts_the_small_carry_above_the_minuend_and_on_the_next_subtrahend():
    """Abziehverfahren mit Erweitern (#842): 503 - 78 writes a small 1 above the 0 and the 3,
    and a small 1 in the next column of the subtrahend, between the numbers and the line."""
    grid = written("-", 503, 78, minus="extend")
    assert text(grid) == "  11\n 503\n~ 78\n 11\n----\n 425"
    small = [(x, y) for x, y, ch, kind in grid["cells"] if kind == CARRY]
    assert sorted(small) == [(1, 3), (2, 0), (2, 3), (3, 0)]
    assert text(grid, [GIVEN]).split("\n")[0].strip() == ""


def test_entbuendeln_rewrites_the_minuend_above_it():
    """Entbündelungsverfahren (#842): 503 - 78 shows 4, 9 and 1 above the minuend, and no carry
    between the numbers and the line."""
    grid = written("-", 503, 78, minus="unbundle")
    assert text(grid) == " 491\n 503\n~ 78\n----\n 425"
    assert [ch for x, y, ch, kind in grid["cells"] if kind == CARRY and y == 0] == ["4", "9", "1"]
    shown = text(grid, [GIVEN])
    assert "491" not in shown and "503" in shown and "~ 78" in shown


def test_ergaenzen_keeps_the_carry_in_the_next_column():
    """Ergänzungsverfahren is the layout a sheet saved before had: the small 1 sits in the next
    column only."""
    assert text(written("-", 503, 78)) == " 503\n~ 78\n 11\n----\n 425"
    assert text(written("-", 503, 78, minus="fill")) == " 503\n~ 78\n 11\n----\n 425"


def test_stellenwerte_name_each_digit_column():
    """Stellenwerte (#842): T H Z E stand over the columns, on the pupil's sheet."""
    grid = written("+", 6789, 2222, stellen=True)
    assert text(grid) == " THZE\n 6789\n+2222\n 111\n-----\n 9011"
    assert all(kind == HEADER for x, y, ch, kind in grid["cells"] if y == 0)
    assert text(grid, [GIVEN, HEADER]).split("\n")[0] == " THZE"


def test_a_hundred_thousands_column_is_labelled_in_one_square():
    grid = written("+", 100000, 1, stellen=True)
    letters = [ch for x, y, ch, kind in sorted(grid["cells"]) if kind == HEADER]
    assert letters == ["HT", "ZT", "T", "H", "Z", "E"]


def test_four_numbers_stack_and_the_sign_can_sit_on_the_last_only():
    """Plus with four numbers (#842): every row has a sign, or only the last one does."""
    assert text(written("+", 9, 9, extra=(9, 9))) == "  9\n+ 9\n+ 9\n+ 9\n 3\n---\n 36"
    assert (
        text(written("+", 9, 9, extra=(9, 9), signs="last")) == "  9\n  9\n  9\n+ 9\n 3\n---\n 36"
    )


def test_three_decimal_numbers_keep_the_comma_in_one_column():
    grid = written("+", 350, 125, 2, extra=(25,))
    assert text(grid) == " 3,50\n+1,25\n+0,25\n 1 1\n-----\n 5,00"


def sums(**more):
    base = {"ops": ["+"], "max": 100, "format": "written", "numbers": 4, "count": 8, "seed": 1}
    return generate(Settings.model_validate({**base, **more}))


def test_a_sum_of_four_has_no_carry_when_uebertrag_is_off():
    """Übertrag not allowed (#842): no place of a four-number sum carries."""
    out = sums(carry="none")
    assert out["loosen"] is None
    for e in out["exercises"]:
        nums = [e["a"], e["b"], e["c"], e["d"]]
        assert sum(nums) == e["result"] <= 100
        assert not any(carries_of(nums))
        assert 0 not in nums


def test_a_sum_of_four_carries_when_uebertrag_is_required():
    out = sums(carry="required")
    assert out["loosen"] is None
    for e in out["exercises"]:
        nums = [e["a"], e["b"], e["c"], e["d"]]
        assert sum(nums) == e["result"]
        assert any(carries_of(nums))


def test_the_first_number_and_each_following_one_keep_their_pattern():
    """Patterns (#842, the patterns of #839): the first number is X0, each following number is one digit."""
    out = sums(numbers=3, count=6, seed=2, pa="X0", pb="X", max=100)
    assert out["loosen"] is None
    for e in out["exercises"]:
        assert len(str(e["a"])) == 2 and str(e["a"]).endswith("0")
        assert len(str(e["b"])) == 1 and len(str(e["c"])) == 1
        assert e["a"] + e["b"] + e["c"] == e["result"]
        assert "d" not in e


def test_the_same_seed_draws_the_same_column_sum():
    assert sums(seed=4, stellen=True, signs="last") == sums(seed=4, stellen=True, signs="last")


def test_old_settings_keep_the_fill_method():
    s = Settings.model_validate(
        {"ops": ["-"], "max": 100, "count": 1, "seed": 1, "format": "written"}
    )
    assert s.minus == "fill" and s.stellen is False and s.signs == "all"


def test_the_place_letters_and_the_method_are_on_the_sheet(editor):
    """The pupil's sheet shows T H Z E, and the panel offers the three minus methods (#842)."""
    client = user()
    props = maths(
        client,
        format="written",
        ops=["-"],
        max=1000,
        count=2,
        seed=3,
        stellen=True,
        minus="unbundle",
        a=[[0, 9], [0, 9], [1, 9]],
        b=[[0, 9], [0, 9], [1, 9]],
    )
    page = editor(box("m", "maths", props, y=20, h=140), client=client)
    heads = at(page, "m").locator("text.head")
    expect(heads.first).to_be_visible()
    letters = set(heads.all_text_contents())
    assert {"H", "Z", "E"} <= letters
    expect(at(page, "m").locator("text.answer")).to_have_count(0)
    at(page, "m").click()
    panel = page.locator(".panel")
    expect(panel.get_by_role("button", name="Entbündelungsverfahren")).to_have_class("on")
    expect(panel.get_by_role("checkbox", name="Stellenwerte zeigen")).to_be_checked()
    expect(panel.get_by_role("button", name="Ergänzungsverfahren")).to_be_visible()
    expect(panel.get_by_role("button", name="Abziehverfahren mit Erweitern")).to_be_visible()
