import os
import subprocess
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
PLAIN = "tests/test_flaky.py::test_plain_target"
ONE = "tests/test_flaky.py::test_target_with_one_param"
TWO = "tests/test_flaky.py::test_target_with_two_params"


def test_plain_target():
    """What the tests below ask the script to collect."""


@pytest.mark.parametrize("n", [30, 200])
def test_target_with_one_param(n):
    pass


@pytest.mark.parametrize("n", [30, 200])
@pytest.mark.parametrize("kind", ["a-b", "c"])
def test_target_with_two_params(n, kind):
    pass


def collected(*ids):
    """The ids test:flaky would run, read from pytest's own list."""
    run = tomllib.loads((ROOT / "mise.toml").read_text())["tasks"]["test:flaky"]["run"]
    # CI's shard would drop most of the ids here too.
    env = {k: v for k, v in os.environ.items() if k != "SHARD"}
    cmd = [*run.split(), *ids, "--collect-only", "-q"]
    res = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    return [line for line in res.stdout.splitlines() if "::" in line]


def twenty(node, param=None):
    return [f"{node}[{f'{param}-' if param else ''}{i}-20]" for i in range(1, 21)]


@pytest.mark.parametrize(
    ("node", "param"), [(ONE, "200"), (TWO, "a-b-30")], ids=["one mark", "two marks"]
)
def test_a_parametrised_test_runs_twenty_times_by_its_full_id(node, param):
    assert collected(f"{node}[{param}]") == twenty(node, param)


def test_an_id_with_no_brackets_still_runs_twenty_times():
    assert collected(PLAIN) == twenty(PLAIN)


def test_several_ids_run_in_one_call_with_and_without_brackets():
    assert sorted(collected(f"{ONE}[30]", PLAIN, f"{TWO}[c-200]")) == sorted(
        twenty(ONE, "30") + twenty(PLAIN) + twenty(TWO, "c-200")
    )


def test_the_readme_and_the_command_list_show_a_parametrised_id():
    for doc in ("README.md", ".claude/CLAUDE.md"):
        example = "mise run test:flaky -- 'tests/test_keys.py::test_name[param]'"
        assert example in (ROOT / doc).read_text()
