"""Which tests a CI shard runs: split by measured time, so the shards end together."""

import hashlib
import json
import statistics
from pathlib import Path

TIMES = Path(__file__).with_name("times.json")


def times(browser):
    """Seconds per test function, measured on CI for this browser (scripts/shard-times.py)."""
    if not TIMES.is_file():
        return {}
    return json.loads(TIMES.read_text()).get(browser, {})


def split(ids, seconds, n):
    """The node ids in n lists of about the same summed time; every id lands in exactly one.

    A test weighs what its function took on average (the id up to its "["), and one that was
    never measured weighs the median. The longest go first, each to the list that is lightest
    so far. Tests of one weight are ordered by a hash of their id and not by their place: the
    slow cases of one parametrised test would else meet in the same shards.
    """
    middle = statistics.median(seconds.values()) if seconds else 1.0

    def weight(node_id):
        return seconds.get(node_id.split("[")[0], middle)

    def order(node_id):
        return (-weight(node_id), hashlib.sha1(node_id.encode()).hexdigest())

    shards, loads = [[] for _ in range(n)], [0.0] * n
    for node_id in sorted(ids, key=order):
        k = loads.index(min(loads))
        shards[k].append(node_id)
        loads[k] += weight(node_id)
    return shards
