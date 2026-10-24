"""The teacher-page module's globals, bound before a verb runs.

Tests replace STATE, BASE, point and joined on that module. The verbs that live in
teacher_page_acts read them here, so a patch is the value the verb sees.
"""

from typing import Any

_g: dict[str, Any] = {}


def bind(g: dict[str, Any]) -> None:
    global _g
    _g = g


def g(name: str) -> Any:
    return _g[name]
