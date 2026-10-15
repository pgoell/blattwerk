"""The git hooks (.config/lefthook.yaml) and CI (.github/workflows/ci.yml): what a push waits
for, and what the merge waits for. The tests read the files; nothing here runs a hook or a job.
"""

import importlib.util
import json
import re
import subprocess
from pathlib import Path

import pytest
from shards import split

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
    assert "name: Test shard ${{ matrix.shard }}/8" in shards
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
    # A run that hangs before the hang guard is armed holds its runner until the limit.
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
    # The deploy waits for the whole run on master to pass, so the job runs on a PR alone.
    assert "    if: github.event_name == 'pull_request'\n" in native
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
    # A run that hangs before the hang guard is armed holds its runner until the limit.
    assert limit <= 15


IDS = [f"tests/test_x.py::test_{k}[{k} ä b]" for k in range(40)] + [
    f"tests/test_y.py::test_{k}" for k in range(7)
]
SECONDS = {f"tests/test_x.py::test_{k}": 0.5 + k for k in range(0, 40, 2)}


@pytest.mark.parametrize("n", [1, 6, 12, 16])
def test_a_split_puts_every_test_in_exactly_one_shard(n):
    shards = split(IDS, SECONDS, n)
    assert len(shards) == n
    assert sorted(i for shard in shards for i in shard) == sorted(IDS)


def test_a_split_weighs_the_shards_alike():
    seconds = {f"tests/test_f.py::f{k}": k + 1.0 for k in range(30)}
    ids = [f"tests/test_f.py::f{k}[{c}]" for k in range(30) for c in range(10)]
    loads = [sum(seconds[i.split("[")[0]] for i in shard) for shard in split(ids, seconds, 12)]
    assert max(loads) <= 1.05 * min(loads)


def test_a_split_is_the_same_each_time_and_in_any_order():
    assert split(IDS, SECONDS, 6) == split(list(reversed(IDS)), SECONDS, 6)


def test_a_test_never_measured_weighs_the_median():
    seconds = {"tests/t.py::a": 1.0, "tests/t.py::b": 5.0, "tests/t.py::c": 9.0}
    ids = [*seconds, *(f"tests/t.py::u{k}" for k in range(6))]
    # The median of the three is 5 s: the six unmeasured weigh that much each.
    loads = [sum(seconds.get(i, 5.0) for i in shard) for shard in split(ids, seconds, 3)]
    assert loads == [15.0, 15.0, 15.0]


def test_a_failed_shard_does_not_cancel_the_others_and_a_failure_has_a_name():
    for job in (part(CI, "shards"), part(CI, "webkit")):
        assert "fail-fast: false" in job
        (run,) = re.findall(r"run: mise run test\S* -- .*", job)
        assert " -v" in run
        assert "--durations=0" in run


def test_webkit_runs_in_sixteen_shards():
    for job, name in (("shards", "Test shard"), ("webkit", "WebKit shard")):
        text = part(CI, job)
        (listed,) = re.findall(r"shard: \[([\d, ]+)\]", text)
        numbers = [int(k) for k in listed.split(",")]
        assert numbers == list(range(1, len(numbers) + 1))
        n = len(numbers)
        if job == "webkit":
            assert n == 16
        assert f"name: {name} ${{{{ matrix.shard }}}}/{n}" in text
        assert f"SHARD: ${{{{ matrix.shard }}}}/{n}" in text


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
    for name in ("dirname", "mkdir", "id"):
        (tmp_path / name).symlink_to(f"/usr/bin/{name}")
    out = subprocess.run(
        ["/usr/bin/bash", REPO / "scripts/test-webkit.sh"],
        env={"PATH": str(tmp_path), "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.split() == [runs]
