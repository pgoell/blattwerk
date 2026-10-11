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
from playwright.sync_api import sync_playwright


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


# The hang of #344: inside a call of the browser.
def test_hangs_in_the_browser():
    with sync_playwright() as p:
        p.chromium.launch().new_page().wait_for_timeout(10**9)


@pytest.mark.parametrize("n", range(3))
def test_passes(n):
    pass
"""


def test_a_test_that_hangs_fails_alone_by_its_name_and_the_run_goes_on(tmp_path):
    (tmp_path / "test_hangs.py").write_text(HANGS)
    # CI's shard and the WebKit lane are not the child's.
    drop = ("SHARD", "BLATTWERK_", "PYTEST_")
    env = {k: v for k, v in os.environ.items() if not k.startswith(drop)}
    cmd = [sys.executable, "-m", "pytest", "-c", "pyproject.toml", "-n", "2", str(tmp_path)]

    def run(*more):
        res = subprocess.run(
            [*cmd, *more], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60
        )
        return res.returncode, res.stdout + res.stderr

    # The repo's own config gives each test a minute.
    _, out = run("--collect-only")
    assert "timeout: 60.0s" in out, out
    # With a short limit: the method is the config's. Two workers, as CI has several.
    code, out = run("-o", "timeout=3")
    assert "timeout method: thread" in out, out
    for name in ("test_hangs", "test_hangs_in_the_browser"):
        assert re.search(rf"crashed while running '[^']*::{name}'", out), out
        assert f"FAILED test_hangs.py::{name} " in out, out
    assert "2 failed, 3 passed" in out, out
    assert code == 1, out
