"""The time each test function took on CI, for the split of the shards (tests/shards.py).

    uv run python scripts/shard-times.py <run id>

Reads the logs of the shard jobs of that CI run (through gh) and writes tests/times.json: per
browser, the mean seconds of each test function over its cases. Needs gh, logged in.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from statistics import mean

REPO = "pgoell/blattwerk"
OUT = Path(__file__).resolve().parents[1] / "tests" / "times.json"
JOBS = {"Test shard": "chromium", "WebKit shard": "webkit"}
# A line of pytest's --durations, with the id after the phase: "12.34s call     tests/x.py::t[a b]".
DURATION = re.compile(r"(\d+\.\d+)s (?:setup|call|teardown)\s+(.+)")


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def read(log_text):
    """Seconds per node id, the three phases of each test added up."""
    seconds = {}
    for line in log_text.splitlines():
        # A log line is "job<TAB>step<TAB>timestamp message".
        fields = line.split("\t", 2)
        if len(fields) < 3:
            continue
        found = DURATION.fullmatch(fields[2].partition(" ")[2].strip())
        if found:
            node = found.group(2).strip()
            seconds[node] = seconds.get(node, 0.0) + float(found.group(1))
    return seconds


def per_function(seconds):
    """The mean over the cases of each test function, rounded to 0.01 s."""
    cases = {}
    for node, took in seconds.items():
        cases.setdefault(node.split("[")[0], []).append(took)
    return {name: round(mean(took), 2) for name, took in cases.items()}


def main(run_id):
    jobs = json.loads(gh("api", f"repos/{REPO}/actions/runs/{run_id}/jobs?per_page=100"))["jobs"]
    seconds = {"chromium": {}, "webkit": {}}
    for job in jobs:
        for prefix, browser in JOBS.items():
            if job["name"].startswith(prefix):
                log = gh("run", "view", run_id, "--repo", REPO, "--job", str(job["id"]), "--log")
                seconds[browser].update(read(log))
    empty = [browser for browser, found in seconds.items() if not found]
    if empty:
        sys.exit(f"no durations for {', '.join(empty)} in run {run_id}: nothing written")
    times = {browser: per_function(found) for browser, found in seconds.items()}
    OUT.write_text(json.dumps(times, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT}: {', '.join(f'{b} {len(t)} functions' for b, t in times.items())}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    main(parser.parse_args().run_id)
