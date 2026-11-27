"""Which tests a CI shard runs: split by measured time, so the shards end together.

The split is by test file, so that a shard collects its own files and leaves the rest alone:
collecting all eleven thousand tests took each of a shard's eight workers about ten seconds of a
core. A file heavier than half a shard's share is cut into parts, and a test belongs to the part
its id hashes to.
"""

import hashlib
import json
import math
import statistics
from pathlib import Path

TIMES = Path(__file__).with_name("times.json")


def times(browser):
    """Seconds per test file, measured on CI for this browser (scripts/shard-times.py).

    A file that the other browser has times for and this one has none ran no test in this one:
    it has no browser test, and weighs nothing here.
    """
    if not TIMES.is_file():
        return {}
    measured = json.loads(TIMES.read_text())
    mine = measured.get(browser, {})
    others = {f for b, files in measured.items() if b != browser for f in files}
    return {**dict.fromkeys(others - set(mine), 0.0), **mine}


def number(text):
    return int(hashlib.sha1(text.encode()).hexdigest(), 16)


def plan(files, seconds, n):
    """For each of n shards, the files it collects: file -> (parts of the file, the parts it runs).

    Every file lands in at least one shard and every part of it in exactly one. A file never
    measured weighs the median file. The heaviest parts go first, each to the shard that is
    lightest so far; parts of one weight are ordered by a hash of their name, not their place.
    """
    measured = [s for s in seconds.values() if s > 0]
    middle = statistics.median(measured) if measured else 1.0
    weight = {f: seconds.get(f, middle) for f in files}
    share = sum(weight.values()) / n
    parts = []
    for f in files:
        k = max(1, min(n, math.ceil(2 * weight[f] / share))) if share else 1
        parts += [(weight[f] / k, f, k, j) for j in range(k)]
    parts.sort(key=lambda p: (-p[0], number(f"{p[1]}:{p[3]}")))
    shards, loads = [{} for _ in range(n)], [0.0] * n
    for w, f, k, j in parts:
        i = loads.index(min(loads))
        shards[i].setdefault(f, (k, set()))[1].add(j)
        loads[i] += w
    return shards


def runs(shard, node_id):
    """Whether the shard runs the test: its file is the shard's, and so is the test's part of it."""
    f = node_id.split("::")[0]
    if f not in shard:
        return False
    k, mine = shard[f]
    return number(node_id) % k in mine
