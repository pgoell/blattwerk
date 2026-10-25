"""The hang guard of tests/conftest.py: a run where no test finishes ends by itself and says why."""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

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

# The issue's repro: collection never returns, so no test report is ever sent (#554).
STALLS_COLLECTION = """
import time


def stall_the_collection():
    time.sleep(1000)


def pytest_collection_modifyitems(config, items):
    stall_the_collection()
"""

# A worker that sleeps at session start never sends ready, so the controller gets no report.
# After configure, so the worker's stack dump is already armed.
STALLS_WORKER = """
import time

import pytest


def stall_the_worker():
    time.sleep(1000)


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    if hasattr(session.config, "workerinput"):
        stall_the_worker()
"""


def run(tmp_path, *args, probe=PROBE, guard="3", plugins=(), env_extra=None, timeout=60):
    """pytest on the probe, with the guard at 3 s. Its own file, outside tests/, so no pyproject."""
    path = tmp_path / "test_probe.py"
    path.write_text(probe)
    env = {k: v for k, v in os.environ.items() if k not in ("SHARD", "CI")}
    # The conftest of tests/ is loaded as a plugin, so the probe gets the guard and the fixtures.
    roots = [str(ROOT / "tests")]
    if plugins:
        roots.append(str(tmp_path))
    env.update(BLATTWERK_HANG=guard, PYTHONPATH=os.pathsep.join(roots))
    if env_extra:
        env.update(env_extra)
    cmd = [sys.executable, "-m", "pytest", str(path), "-p", "no:cacheprovider", "-p", "conftest"]
    for plugin in plugins:
        cmd.extend(["-p", plugin])
    return subprocess.run(
        [*cmd, *args], cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout
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
    # The clock starts at configure and restarts when a worker is ready and when a test reports,
    # so the silence after this test is what fires it, not the workers' import.
    res = run(tmp_path, "-n", "2")
    assert res.returncode == 1, res.stdout + res.stderr
    assert "the run hangs" in res.stderr
    assert "Started and not finished: " in res.stderr
    # The controller runs no test, so the fixture's line can only come from the worker's stacks.
    assert "in stuck" in res.stderr


def test_a_finished_run_is_not_ended_by_the_guard(tmp_path):
    # Shorter than the import allowance: a run that does report must not be cut off while the
    # workers start.
    probe = "def test_one():\n    pass\n"
    res = run(tmp_path, "-n", "2", probe=probe)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "the run hangs" not in res.stderr


def test_a_hang_in_collection_ends_the_run(tmp_path):
    """Workers collect. A sleep there used to wait out the job limit: no test report ever came (#554)."""
    (tmp_path / "stall_collection.py").write_text(STALLS_COLLECTION)
    began = time.monotonic()
    res = run(
        tmp_path,
        "-n",
        "2",
        probe="def test_one():\n    pass\n",
        guard="5",
        plugins=("stall_collection",),
        env_extra={"SHARD": "1/8"},
    )
    took = time.monotonic() - began
    assert res.returncode == 1, res.stdout + res.stderr
    assert "No test has finished for 5 s: the run hangs." in res.stderr
    # The controller runs no collection, so this line is the worker, stuck where the issue hangs.
    assert "in stall_the_collection" in res.stderr
    assert took < 40, took


@pytest.mark.timeout(90)
def test_a_hang_while_the_workers_start_ends_the_run(tmp_path):
    """A worker that never becomes ready sends no report. The clock from configure ends the run (#554).

    The limit is the 30 s import allowance, so the test outlasts the minute other tests get.
    """
    (tmp_path / "stall_worker.py").write_text(STALLS_WORKER)
    began = time.monotonic()
    res = run(
        tmp_path,
        "-n",
        "2",
        probe="def test_one():\n    pass\n",
        guard="30",
        plugins=("stall_worker",),
        timeout=70,
    )
    took = time.monotonic() - began
    assert res.returncode == 1, res.stdout + res.stderr
    assert "No test has finished for 30 s: the run hangs." in res.stderr
    assert "in stall_the_worker" in res.stderr
    assert took < 65, took
