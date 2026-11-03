"""A written plus of three or four numbers, one column."""

import random

from blattwerk.maths.model import Settings, fits, loosened, pick
from blattwerk.maths.pattern import allow, for_op, matches
from blattwerk.maths.written import sum_carries, written


def one_sum(s: Settings, shaped: Settings, rng: random.Random, top: int) -> list[int] | None:
    """One column of `numbers` that keeps the limits, or None when this try misses."""
    n, low = s.numbers, 1
    nums = quiet(shaped, rng, n, low, top) if s.carry == "none" else loud(shaped, rng, n, low, top)
    if nums is None or not accept(s, nums, top):
        return None
    return nums


def room_for(ranges: list[tuple[int, int]], nums: list[int]) -> list[tuple[int, int]] | None:
    """`ranges` narrowed so a further number makes no carry with `nums`."""
    out = []
    for i, (lo, hi) in enumerate(ranges):
        used = sum(n // 10**i % 10 for n in nums)
        hi = min(hi, 9 - used)
        if lo > hi:
            return None
        out.append((lo, hi))
    return out


def quiet(s: Settings, rng: random.Random, n: int, low: int, top: int) -> list[int] | None:
    """Numbers that add without a carry. Each following number is drawn from the digits left."""
    first = pick(rng, s.a, low, top)
    if first is None:
        return None
    nums = [first]
    for k in range(1, n):
        ranges = room_for(list(s.b), nums)
        if ranges is None:
            return None
        hi = top - sum(nums) - low * (n - k - 1)
        nxt = None if hi < low else pick(rng, ranges, low, hi)
        if nxt is None:
            return None
        nums.append(nxt)
    return nums


def loud(s: Settings, rng: random.Random, n: int, low: int, top: int) -> list[int] | None:
    """Numbers drawn so their sum stays within `top`. The later ones share what is left."""
    room = top - low * (n - 1)
    first = None if room < low else pick(rng, s.a, low, room)
    if first is None:
        return None
    nums = [first]
    left = top - first
    for k in range(1, n):
        hi = left - low * (n - k - 1)
        nxt = None if hi < low else pick(rng, s.b, low, hi)
        if nxt is None:
            return None
        nums.append(nxt)
        left -= nxt
    return nums


def accept(s: Settings, nums: list[int], top: int) -> bool:
    """Whether these numbers are a written sum the settings allow."""
    if any(n <= 0 or n > top for n in nums) or sum(nums) > top:
        return False
    if s.distinct and len(set(nums)) < len(nums):
        return False
    if not s.zero and (0 in nums or sum(nums) == 0):
        return False
    zero_ok = allow(s, "+")
    if not matches(s.pa, nums[0], zero_ok):
        return False
    if any(not matches(s.pb, n, zero_ok) for n in nums[1:]):
        return False
    if not matches(s.pr, sum(nums), zero_ok):
        return False
    carried = sum_carries(nums)
    if s.carry == "none" and any(carried):
        return False
    if s.carry == "required" and not any(carried):
        return False
    return all(fits(s.a if i == 0 else s.b, n) for i, n in enumerate(nums))


def draw(s: Settings, top: int) -> list[list[int]]:
    """Up to `count` different column sums. The same seed draws the same ones."""
    shaped = for_op(s, "+")
    if any(lo > hi for lo, hi in [*shaped.a, *shaped.b]):
        return []
    rng = random.Random(s.seed)
    found: dict[tuple[int, ...], None] = {}
    for _ in range(max(4000, 80 * s.count)):
        if len(found) == s.count:
            break
        nums = one_sum(s, shaped, rng, top)
        if nums is not None:
            found[tuple(nums)] = None
    return [list(nums) for nums in found]


def exercise(s: Settings, nums: list[int], decimals: int) -> dict:
    """One column sum, with its grid."""
    grid = written(
        "+",
        nums[0],
        nums[1],
        decimals,
        s.money and decimals > 0,
        extra=tuple(nums[2:]),
        stellen=s.stellen,
        signs=s.signs,
    )
    out = {"op": "+", "a": nums[0], "b": nums[1], "result": sum(nums), "rest": 0, "grid": grid}
    if len(nums) > 2:
        out["c"] = nums[2]
    if len(nums) > 3:
        out["d"] = nums[3]
    return out


def summed(s: Settings, decimals: int) -> dict:
    """The column sums for these settings, and the limits that stand in the way of more."""
    drawn = draw(s, s.max)
    exercises = [exercise(s, nums, decimals) for nums in drawn]
    if len(drawn) == s.count:
        return {"exercises": exercises, "loosen": None}
    table = loosened(s)
    names = ("carry", "a", "b", "pa", "pb", "pr", "nil", "max", "zero", "distinct")
    loosen = [name for name in names if len(draw(*table[name])) > len(drawn)]
    return {"exercises": exercises, "loosen": loosen}
