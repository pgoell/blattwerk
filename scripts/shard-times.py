"""The time each test file took on CI, for the split of the shards (tests/shards.py).

    uv run python scripts/shard-times.py <run id>
    uv run python scripts/shard-times.py --logs <folder>

Reads the logs of the shard jobs of that CI run (through gh, logged in) and writes tests/times.json:
per lane, the seconds of each test file, its tests' three phases added up. With --logs it reads
the run's log archive instead, unpacked into the folder (one "<n>_<job name>.txt" per job).
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = "pgoell/blattwerk"
OUT = Path(__file__).resolve().parents[1] / "tests" / "times.json"
JOBS = {"Test shard": "chromium", "WebKit shard": "webkit", "Native": "native"}
# A line of pytest's --durations, with the id after the phase: "12.34s call     tests/x.py::t[a b]".
DURATION = re.compile(r"(\d+\.\d+)s (?:setup|call|teardown)\s+(.+)")


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def read(log_text):
    """Seconds per node id, the three phases of each test added up."""
    seconds = {}
    for line in log_text.splitlines():
        # A line of `gh run view --log` is "job<TAB>step<TAB>timestamp message"; a line of the
        # run's archive is "timestamp message".
        found = DURATION.fullmatch(line.rpartition("\t")[2].partition(" ")[2].strip())
        if found:
            node = found.group(2).strip()
            seconds[node] = seconds.get(node, 0.0) + float(found.group(1))
    return seconds


def per_file(seconds):
    """The sum over the tests of each file, rounded to 0.1 s."""
    files = {}
    for node, took in seconds.items():
        name = node.split("::")[0]
        files[name] = files.get(name, 0.0) + took
    return {name: round(took, 1) for name, took in files.items()}


def logs_of_run(run_id):
    """(job name, log) of each job of the run, through gh."""
    jobs = json.loads(gh("api", f"repos/{REPO}/actions/runs/{run_id}/jobs?per_page=100"))["jobs"]
    for job in jobs:
        yield (
            job["name"],
            gh("run", "view", run_id, "--repo", REPO, "--job", str(job["id"]), "--log"),
        )


def logs_of_folder(folder):
    """(job name, log) of each job in an unpacked log archive."""
    for path in sorted(Path(folder).glob("*_*.txt")):
        yield path.stem.partition("_")[2], path.read_text(errors="replace")


def main(logs, source):
    seconds = {"chromium": {}, "webkit": {}, "native": {}}
    for name, log in logs:
        for prefix, browser in JOBS.items():
            if name.startswith(prefix):
                seconds[browser].update(read(log))
    empty = [browser for browser, found in seconds.items() if not found]
    if empty:
        sys.exit(f"no durations for {', '.join(empty)} in {source}: nothing written")
    times = {browser: per_file(found) for browser, found in seconds.items()}
    OUT.write_text(json.dumps(times, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT}: {', '.join(f'{b} {len(t)} files' for b, t in times.items())}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", nargs="?")
    parser.add_argument("--logs", help="an unpacked log archive of the run, read instead of gh")
    args = parser.parse_args()
    if args.logs:
        main(logs_of_folder(args.logs), args.logs)
    elif args.run_id:
        main(logs_of_run(args.run_id), f"run {args.run_id}")
    else:
        parser.error("give a run id or --logs")
