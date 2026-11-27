"""The git hooks (.config/lefthook.yaml) and CI (.github/workflows/ci.yml): what a push waits
for, and what the merge waits for. The tests read the files; nothing here runs a hook or a job.
"""

import importlib.util
import json
import re
import subprocess
from pathlib import Path

import pytest
import shards
from shards import plan, runs

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


def test_pre_push_runs_lint_the_commit_check_and_the_file_size():
    lines = [line.strip() for line in part(HOOKS, "pre-push").splitlines() if line.strip()]
    assert lines == [
        "commands:",
        "lint:",
        "run: mise run lint",
        "check-commits:",
        "run: mise run check-commits",
        "file-size:",
        "run: scripts/check-file-size",
    ]


def test_ci_has_the_checks_the_merge_needs():
    needed = PROTECTION["required_status_checks"]["contexts"]
    assert needed == ["Lint", "Test", "Commits"]
    jobs = part(CI, "jobs")
    for name in needed:
        assert re.search(rf"^    name: {name}$", jobs, re.M), name
    # Test passes when every shard did. A pull request that only touches docs or
    # .cursor/skills skips the shards; Test still passes, under the same name.
    gate = part(CI, "test")
    assert "needs: [changes, shards, webkit]" in gate
    assert 'if [ "$CHANGES" != success ]' in gate
    assert "skipped)" in gate
    assert 'test "$SUITE" = false' in gate
    assert "exit 1" in gate
    assert "continue-on-error" not in code(CI)
    lint = part(CI, "lint")
    assert "run: mise run lint" in lint
    assert "run: scripts/check-file-size" in lint
    shards = part(CI, "shards")
    assert "needs: changes" in shards
    assert "needs.changes.outputs.suite == 'true'" in shards
    assert "name: Test shard ${{ matrix.shard }}/12" in shards
    assert "run: mise run test " in shards


def test_a_chromium_shard_ends_well_before_its_limit():
    """#541, #550: with six shards a job took up to 504 s and the limit cancelled it at 480 s.

    Eight shards take three quarters of that; the limit leaves the slowest job half again.
    """
    shards = part(CI, "shards")
    (listed,) = re.findall(r"shard: \[([\d, ]+)\]", shards)
    n = len(listed.split(","))
    (limit,) = map(int, re.findall(r"^    timeout-minutes: (\d+)$", shards, re.M))
    slowest = 504 * 6 / n
    assert limit * 60 >= 1.5 * slowest + 60
    # The hang guard ends a silent run from configure on (#554). The limit stays a short
    # backstop for a run whose guard never gets to fire.
    assert limit <= 15


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
    # The deploy waits for the whole run on master to pass, so the job runs on a PR alone,
    # and only when that PR runs the suite.
    assert (
        "    if: github.event_name == 'pull_request' && needs.changes.outputs.suite == 'true'\n"
        in native
    )
    assert "Native" not in PROTECTION["required_status_checks"]["contexts"]


def test_the_native_tests_use_the_mouse_and_the_keyboard_only():
    # The headed tests live in test_native.py and the siblings it was split into.
    text = "\n".join(p.read_text() for p in sorted((REPO / "tests").glob("test_native*.py")))
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


def test_a_slow_pull_of_the_image_leaves_the_webkit_tests_their_time():
    """#439: the job's limit counts the pull of the image, which took up to ten minutes."""
    webkit = part(CI, "webkit")
    (step,) = [s for s in re.split(r"\n      - ", webkit) if "test:webkit" in s]
    (limit,) = map(int, re.findall(r"timeout-minutes: (\d+)", step))
    (job,) = map(int, re.findall(r"^    timeout-minutes: (\d+)$", webkit, re.M))
    assert limit + 10 <= job


def test_a_webkit_shard_ends_well_before_its_limit():
    """With twelve shards the Pytest step took up to 515 s against its limit of 540 s.

    Sixteen shards take three quarters of that; the limit leaves the slowest step half again.
    """
    webkit = part(CI, "webkit")
    (listed,) = re.findall(r"shard: \[([\d, ]+)\]", webkit)
    n = len(listed.split(","))
    (step,) = [s for s in re.split(r"\n      - ", webkit) if "test:webkit" in s]
    (limit,) = map(int, re.findall(r"timeout-minutes: (\d+)", step))
    slowest = 515 * 12 / n
    assert limit * 60 >= 1.5 * slowest + 60
    # The hang guard ends a silent run from configure on (#554). The limit stays a short
    # backstop for a run whose guard never gets to fire.
    assert limit <= 15


FILES = [f"tests/test_{k}.py" for k in range(40)]
SECONDS = {f"tests/test_{k}.py": 0.5 + k for k in range(0, 40, 2)}
IDS = [f"{f}::test_{c}[{c} ä b]" for f in FILES for c in range(30)]


def ran(shards, ids):
    return [[i for i in ids if runs(shard, i)] for shard in shards]


@pytest.mark.parametrize("n", [1, 6, 12, 16, 24])
def test_a_split_puts_every_test_in_exactly_one_shard(n):
    shards = plan(FILES, SECONDS, n)
    assert len(shards) == n
    assert {f for shard in shards for f in shard} == set(FILES)
    assert sorted(i for found in ran(shards, IDS) for i in found) == sorted(IDS)


def test_a_split_weighs_the_shards_alike():
    seconds = {f"tests/test_{k}.py": k % 30 + 1.0 for k in range(300)}
    loads = [
        sum(seconds[f] * len(parts) / k for f, (k, parts) in shard.items())
        for shard in plan(sorted(seconds), seconds, 12)
    ]
    assert max(loads) <= 1.05 * min(loads)


def test_a_heavy_file_is_cut_into_parts_that_shards_share():
    seconds = {"tests/test_big.py": 100.0, **{f"tests/test_{k}.py": 1.0 for k in range(20)}}
    shards = plan(sorted(seconds), seconds, 4)
    holding = [shard for shard in shards if "tests/test_big.py" in shard]
    assert len(holding) == 4
    ids = [f"tests/test_big.py::t[{c}]" for c in range(400)]
    counts = [len(found) for found in ran(shards, ids)]
    assert sum(counts) == 400
    assert min(counts) > 50


def test_a_split_is_the_same_each_time_and_in_any_order():
    assert plan(FILES, SECONDS, 6) == plan(list(reversed(FILES)), SECONDS, 6)


def test_a_file_never_measured_weighs_the_median():
    seconds = {"tests/test_a.py": 3.0, "tests/test_b.py": 5.0, "tests/test_c.py": 7.0}
    files = [*seconds, *(f"tests/test_u{k}.py" for k in range(6))]
    # The median of the three is 5 s: the six unmeasured weigh that much each, and the 45 s of all
    # nine make three shards of 15 s.
    shards = plan(files, seconds, 3)
    loads = [
        sum(seconds.get(f, 5.0) * len(parts) / k for f, (k, parts) in shard.items())
        for shard in shards
    ]
    assert loads == pytest.approx([15.0, 15.0, 15.0])


def test_a_file_only_the_other_browser_ran_weighs_nothing(tmp_path, monkeypatch):
    times = tmp_path / "times.json"
    times.write_text(
        json.dumps(
            {
                "chromium": {"tests/test_a.py": 3.0, "tests/test_b.py": 2.0},
                "webkit": {"tests/test_a.py": 4.0},
            }
        )
    )
    monkeypatch.setattr(shards, "TIMES", times)
    assert shards.times("webkit") == {"tests/test_a.py": 4.0, "tests/test_b.py": 0.0}
    assert shards.times("chromium") == {"tests/test_a.py": 3.0, "tests/test_b.py": 2.0}


def test_a_failed_shard_does_not_cancel_the_others_and_a_failure_has_a_name():
    for job in (part(CI, "shards"), part(CI, "webkit")):
        assert "fail-fast: false" in job
        (run,) = re.findall(r"run: mise run test\S* -- .*", job)
        assert " -v" in run
        assert "--durations=0" in run


def test_the_suite_is_split_into_twelve_and_twenty_four_shards():
    """Run 39783927061: eight and sixteen shards left pytest at about ten minutes.

    Twelve and twenty-four, weighed by the times from that run, bring it to about six.
    """
    expected = {"shards": ("Test shard", 12), "webkit": ("WebKit shard", 24)}
    for job, (name, n) in expected.items():
        text = part(CI, job)
        (listed,) = re.findall(r"shard: \[([\d, ]+)\]", text)
        numbers = [int(k) for k in listed.split(",")]
        assert numbers == list(range(1, n + 1))
        assert f"name: {name} ${{{{ matrix.shard }}}}/{n}" in text
        assert f"SHARD: ${{{{ matrix.shard }}}}/{n}" in text


def test_a_pull_request_skips_the_suite_only_for_docs_and_skills():
    spec = importlib.util.spec_from_file_location("ci_suite", REPO / "scripts/ci_suite.py")
    assert spec and spec.loader
    ci_suite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ci_suite)
    assert ci_suite.suite_runs([])
    assert not ci_suite.suite_runs(["docs/okf/readme.md", ".cursor/skills/why/SKILL.md"])
    assert ci_suite.suite_runs(["docs/okf/readme.md", "src/blattwerk/app.py"])
    assert ci_suite.suite_runs([".cursor/rules/python.md"])
    assert ci_suite.suite_runs(["README.md"])
    changes = part(CI, "changes")
    assert '!= "pull_request"' in changes
    assert "suite=true" in changes
    assert "python3 scripts/ci_suite.py" in changes


def test_the_shard_times_script_reads_the_durations_of_a_log():
    spec = importlib.util.spec_from_file_location("shard_times", REPO / "scripts/shard-times.py")
    assert spec and spec.loader
    shard_times = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shard_times)
    log = "\n".join(
        [
            "Test shard 1/6\tPytest\t2026-10-10T10:00:01Z 0.12s setup    tests/t.py::t_x[a b]",
            "Test shard 1/6\tPytest\t2026-10-10T10:00:02Z 1.50s call     tests/t.py::t_x[a b]",
            "Test shard 1/6\tPytest\t2026-10-10T10:00:03Z 0.30s teardown tests/t.py::t_x[a b]",
            "Test shard 1/6\tPytest\t2026-10-10T10:00:04Z 2.00s call     tests/t.py::t_y",
            "Test shard 1/6\tPytest\t2026-10-10T10:00:05Z ==== 2 passed in 4.00s ====",
        ]
    )
    assert shard_times.read(log) == pytest.approx(
        {"tests/t.py::t_x[a b]": 1.92, "tests/t.py::t_y": 2.0}
    )


# ldconfig as a host with GTK 4 prints it: the line WebKit needs, and after a pause the rest. A
# reader that stops at the first match has left by then, so the rest meets a closed pipe.
GTK = "echo 'libgtk-4.so.1 => /lib/libgtk-4.so.1'; /usr/bin/sleep 0.3; /usr/bin/seq 20000"


@pytest.mark.parametrize(
    "ldconfig, docker, runs",
    [
        (GTK, True, "pytest"),
        ("echo 'libc.so.6 (libc6,x86-64) => /lib/libc.so.6'", True, "docker"),
        # CI's job runs in Playwright's image, which has no docker: never look for one there.
        ("echo 'libc.so.6 (libc6,x86-64) => /lib/libc.so.6'", False, "pytest"),
    ],
)
def test_the_webkit_script_runs_in_docker_only_without_gtk_and_with_docker(
    tmp_path, ldconfig, docker, runs
):
    """5 of 133 WebKit shards in 40 CI runs failed with `docker: not found` (exit 127): GTK was
    there, but `ldconfig -p | grep -q` under pipefail took SIGPIPE for "no GTK"."""
    tools = {
        "ldconfig": ldconfig,
        "uv": "echo pytest",
        **({"docker": "echo docker"} if docker else {}),
    }
    for name, body in tools.items():
        (tmp_path / name).write_text(f"#!/bin/sh\n{body}\n")
        (tmp_path / name).chmod(0o755)
    # grep too: the script of before piped into it, and must fail by the pipe, not by its absence.
    for name in ("dirname", "mkdir", "id", "grep"):
        (tmp_path / name).symlink_to(f"/usr/bin/{name}")
    out = subprocess.run(
        ["/usr/bin/bash", REPO / "scripts/test-webkit.sh"],
        env={"PATH": str(tmp_path), "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.split() == [runs]
