"""The sheet model's own tests: vitest and fast-check on frontend/src, with no browser."""

import subprocess
from pathlib import Path

import pytest
from ui import BROWSER

FRONTEND = Path(__file__).parent.parent / "frontend"


# The WebKit lane would only repeat it: node knows no browser.
@pytest.mark.skipif(BROWSER == "webkit", reason="runs in node, the same in every lane")
def test_the_properties_of_the_sheet_model_hold():
    """One run of `mise run test:model`. A property that fails prints its seed, and the seed is
    in what vitest wrote, so it stands in the failure here."""
    # The run takes a second. A minute is its whole budget, on a machine busy with the suite too.
    run = subprocess.run(
        ["npm", "test", "--prefix", str(FRONTEND)], capture_output=True, text=True, timeout=60
    )
    assert run.returncode == 0, run.stdout + run.stderr
