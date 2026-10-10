"""The git hooks (.config/lefthook.yaml) and CI (.github/workflows/ci.yml): what a push waits
for, and what the merge waits for. The tests read the files; nothing here runs a hook or a job.
"""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOOKS = (REPO / ".config/lefthook.yaml").read_text()
CI = (REPO / ".github/workflows/ci.yml").read_text()
PROTECTION = json.loads((REPO / ".github/branch-protection.json").read_text())


def code(text):
    """The file without its comments."""
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def part(text, key):
    """The lines under `key:`, up to the next line indented no deeper."""
    found = re.search(rf"^( *){re.escape(key)}:\n((?:\1 +.*\n|\n)*)", code(text) + "\n", re.M)
    assert found, key
    return found.group(2)


def test_pre_push_runs_lint_and_the_commit_check_only():
    lines = [line.strip() for line in part(HOOKS, "pre-push").splitlines() if line.strip()]
    assert lines == [
        "commands:",
        "lint:",
        "run: mise run lint",
        "check-commits:",
        "run: mise run check-commits",
    ]


def test_ci_has_the_checks_the_merge_needs():
    needed = PROTECTION["required_status_checks"]["contexts"]
    assert needed == ["Lint", "Test", "Commits"]
    jobs = part(CI, "jobs")
    for name in needed:
        assert re.search(rf"^    name: {name}$", jobs, re.M), name
    # Test passes only when every shard did; the shards run the suite.
    gate = part(CI, "test")
    assert "needs: [shards, webkit]" in gate
    for job in ("shards", "webkit"):
        assert f'test "${{{{ needs.{job}.result }}}}" = success' in gate
    assert "continue-on-error" not in code(CI)
    shards = part(CI, "shards")
    assert "name: Test shard ${{ matrix.shard }}/6" in shards
    assert "run: mise run test " in shards


def test_the_native_job_runs_the_headed_tests_and_no_merge_waits_for_it():
    native = part(CI, "native")
    assert "name: Native" in native
    assert "run: mise run test:native" in native
    assert re.search(r"^    timeout-minutes: \d+$", native, re.M)
    # The whole Chromium, each try with an end, as the shards load theirs.
    install = "uv run playwright install chromium"
    assert f'install="{install}"' in native
    assert "timeout -k 5 80 $install || timeout -k 5 80 $install" in native
    assert "native" not in part(CI, "test")
    assert "Native" not in PROTECTION["required_status_checks"]["contexts"]


def test_the_native_tests_use_the_mouse_and_the_keyboard_only():
    text = (REPO / "tests/test_native.py").read_text()
    # A locator finds and checks; it neither acts nor sets anything in the page.
    for call in (
        "dispatch_event",
        "evaluate",
        "eval_on_selector",
        "wait_for_function",
        "select_option",
        "set_input_files",
        "fill",
        "focus",
        "check",
        "tap",
        "hover",
        "dblclick",
        "drag_to",
    ):
        assert not re.search(rf"\.{call}\w*\(", text), call
    # A click is the mouse's, a key the keyboard's.
    assert not re.search(r"(?<!\.mouse)\.click\(", text)
    assert not re.search(r"(?<!\.keyboard)\.(press|type)\(", text)
    # The file dialog is the system's: its file goes in through the chooser, once.
    assert text.count("set_files(") == 1
    assert "expect_file_chooser" in text


def test_the_chromium_step_is_bounded_and_runs_no_apt():
    assert "--with-deps" not in code(CI)
    assert "install-deps" not in code(CI)
    assert not re.search(r"\bapt(-get)?\b", code(CI))
    shards = part(CI, "shards")
    (step,) = [s for s in re.split(r"\n      - ", shards) if "playwright install" in s]
    # One retry of its own, each try with an end.
    assert "timeout -k 5 80 $install || timeout -k 5 80 $install" in step
    (limit,) = map(int, re.findall(r"timeout-minutes: (\d+)", step))
    assert limit * 60 > 2 * 80
    # A step that runs out leaves the tests their two minutes.
    (job,) = map(int, re.findall(r"^    timeout-minutes: (\d+)$", shards, re.M))
    assert limit + 2 < job
