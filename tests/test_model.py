"""The sheet model's own tests: vitest and fast-check on frontend/src, with no browser."""

import os
import signal
import subprocess
from pathlib import Path

FRONTEND = Path(__file__).parent.parent / "frontend"


def test_the_properties_of_the_sheet_model_hold():
    """One run of `mise run test:model`. A property that fails prints its seed, and the seed is
    in what vitest wrote, so it stands in the failure here."""
    # A group of its own: npm starts vitest, and a kill of npm alone would leave vitest running.
    run = subprocess.Popen(
        ["npm", "test", "--prefix", str(FRONTEND)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        # The run takes a second. A minute is its whole budget, on a machine busy with the suite.
        said, _ = run.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        os.killpg(run.pid, signal.SIGKILL)
        said, _ = run.communicate()
        raise AssertionError(f"no end after a minute, and until then:\n{said}") from None
    assert run.returncode == 0, said
