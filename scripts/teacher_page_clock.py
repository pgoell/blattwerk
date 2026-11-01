"""The teacher run's clock: seconds since ``start``, kept in the run folder.

The shell's ``date`` can run slow against the work, so a run does not time itself by it (#617).
"""

import time

from teacher_page_ns import g


def began() -> None:
    """Marks ``start``, once. A second start keeps the clock of the run."""
    path = g("STATE") / "began"
    if not path.exists():
        path.write_text(str(time.time()))


def clock() -> str:
    """Seconds since ``start``, or 0 when the window was never started."""
    try:
        start = float((g("STATE") / "began").read_text())
    except OSError, ValueError:
        return "The clock is 0"
    return f"The clock is {max(0, int(time.time() - start))}"
