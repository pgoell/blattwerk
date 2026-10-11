"""The hang guard of tests/conftest.py: a run where no test finishes ends by itself and says why."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
# Its session fixture never ends, so no test finishes after test_one: the guard must fire.
PROBE = """
import threading

import pytest


@pytest.fixture(scope="session", autouse=True)
def stuck():
    yield
    threading.Event().wait()


def test_one():
    pass
"""


# A test that fails, with a fixture that never ends after it.
FAILS = """
import threading

import pytest


@pytest.fixture
def stuck():
    yield
    threading.Event().wait()


def test_one(stuck):
    assert False
"""


def run(tmp_path, *args, probe=PROBE, guard="3"):
    """pytest on the probe, with the guard at 3 s. Its own file, outside tests/, so no pyproject."""
    path = tmp_path / "test_probe.py"
    path.write_text(probe)
    env = {k: v for k, v in os.environ.items() if k not in ("SHARD", "CI")}
    # The conftest of tests/ is loaded as a plugin, so the probe gets the guard and the fixtures.
    env.update(BLATTWERK_HANG=guard, PYTHONPATH=str(ROOT / "tests"))
    cmd = [sys.executable, "-m", "pytest", str(path), "-p", "no:cacheprovider", "-p", "conftest"]
    return subprocess.run(
        [*cmd, *args], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60
    )


def test_a_run_with_no_workers_has_no_guard_so_a_debugger_may_wait(tmp_path):
    # Five seconds in one test, as a teacher of the code sits in pdb: over the guard's three.
    slow = "import time\n\n\ndef test_one():\n    time.sleep(5)\n"
    res = run(tmp_path, "-n", "0", probe=slow)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "the run hangs" not in res.stderr


def test_a_failed_test_keeps_its_limit_for_its_teardown(tmp_path):
    # The guard is far off: the test's own limit of 3 s must end the run, and say where it sat.
    res = run(
        tmp_path, "-n", "0", "--timeout=3", "--timeout-method=thread", probe=FAILS, guard="60"
    )
    assert res.returncode == 1, res.stdout + res.stderr
    assert "Timeout" in res.stdout + res.stderr
    assert "in stuck" in res.stdout + res.stderr
    assert "the run hangs" not in res.stderr


def test_a_run_where_no_test_finishes_ends_with_the_stacks_of_its_workers(tmp_path):
    # Ten seconds: the guard counts from the start, and on a busy runner the two workers take
    # more than three to come up. Then it would fire before the test had begun.
    res = run(tmp_path, "-n", "2", guard="10")
    assert res.returncode == 1, res.stdout + res.stderr
    assert "the run hangs" in res.stderr
    assert "Started and not finished: " in res.stderr
    # The controller runs no test, so the fixture's line can only come from the worker's stacks.
    assert "in stuck" in res.stderr
