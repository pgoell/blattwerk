"""A test that hangs fails alone, by its name, and the run goes on (#340)."""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
# The hang of #340: the portal's loop never ends while it cancels its tasks, and the test joins
# the portal's thread.
HANGS = """
import asyncio

import pytest
from anyio.from_thread import start_blocking_portal


async def deaf():
    while True:
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass


async def leave_a_deaf_task():
    asyncio.create_task(deaf())


def test_hangs():
    with start_blocking_portal() as portal:
        portal.call(leave_a_deaf_task)


@pytest.mark.parametrize("n", range(3))
def test_passes(n):
    pass
"""


def test_a_test_that_hangs_fails_alone_by_its_name_and_the_run_goes_on(tmp_path):
    (tmp_path / "test_hangs.py").write_text(HANGS)
    # CI's shard and the WebKit lane are not the child's.
    drop = ("SHARD", "BLATTWERK_", "PYTEST_")
    env = {k: v for k, v in os.environ.items() if not k.startswith(drop)}
    # The repo's own config, with a short limit: the method is the config's. Two workers, as CI
    # has several: each takes two tests at the start, so one test follows the hang in its worker.
    cmd = [sys.executable, "-m", "pytest", "-c", "pyproject.toml", "-n", "2", "-o", "timeout=2"]
    res = subprocess.run(
        [*cmd, str(tmp_path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60
    )
    out = res.stdout + res.stderr
    assert "timeout method: signal" in out, out
    assert re.search(r"FAILED .*::test_hangs - Failed: Timeout", out), out
    assert "1 failed, 3 passed" in out, out
    assert res.returncode == 1, out
