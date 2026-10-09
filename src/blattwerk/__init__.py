"""Worksheet tool for Grundschule teachers"""

import logging
import sys


class Stderr(logging.StreamHandler):
    """Looks up sys.stderr with each line and not once at import, as logging's last resort does."""

    stream = property(lambda self: sys.stderr, lambda self, value: None)


# Here and not in app.py, so the command line (`python -m blattwerk`) logs the same way.
log = logging.getLogger("blattwerk")
# A reload must not add a second handler, or each line shows twice.
if not log.handlers:
    log.setLevel(logging.INFO)
    handler = Stderr()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    log.addHandler(handler)
