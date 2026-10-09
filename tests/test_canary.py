"""The deploy's canary and its way back: alive.sh, canary.sh, go-back.sh and their place in
deploy.yml. The scripts run against a docker that only writes down what it was asked.
"""

import hashlib
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from blattwerk import db

ROOT = Path(__file__).parent.parent
DEPLOY = (ROOT / ".github" / "workflows" / "deploy.yml").read_text()
COMPOSE = (ROOT / "docker-compose.yml").read_text()
NAME = "blattwerk-canary"
IMAGE = "blattwerk-blattwerk"
SMOKE = "print('the smoke test')\n"

# RC_<SUBCOMMAND> sets what a call answers: RC_EXEC for alive.sh, RC_IMAGE for `image inspect`.
DOCKER = """#!/usr/bin/env bash
echo "$*" >> "$DOCKER_LOG"
case "$*" in
  *"blattwerk invite") echo /einladung/tok123; exit "${RC_INVITE:-0}" ;;
  *"-e SMOKE_INVITE"*)
    printenv SMOKE_INVITE > "$DOCKER_LOG.invite"
    cat > "$DOCKER_LOG.stdin"
    echo "smoke ran"
    exit "${RC_SMOKE:-0}" ;;
esac
rc=RC_${1^^}
exit "${!rc:-0}"
"""


def run(tmp_path, script, *args, **answers):
    """Runs a script, gives its result and the docker calls it made.

    The scripts lie in a folder of their own with a stand-in for smoke.py, which canary.sh feeds
    to the container.
    """
    scripts, stub, log = tmp_path / "scripts", tmp_path / "bin" / "docker", tmp_path / "docker.log"
    if not scripts.exists():
        scripts.mkdir()
        for path in (ROOT / "scripts").glob("*.sh"):
            (scripts / path.name).symlink_to(path)
        (scripts / "smoke.py").write_text(SMOKE)
        stub.parent.mkdir()
        stub.write_text(DOCKER)
        stub.chmod(0o755)
    log.unlink(missing_ok=True)
    env = {
        **os.environ,
        "PATH": f"{stub.parent}:{os.environ['PATH']}",
        "DOCKER_LOG": str(log),
        "ALIVE_WAIT": "0",
        **{key.upper(): str(value) for key, value in answers.items()},
    }
    env.pop("SMOKE_INVITE", None)
    command = ["bash", str(scripts / script), *map(str, args)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=20, env=env)
    return result, log.read_text().splitlines() if log.exists() else []


def make_live(folder):
    folder.mkdir(parents=True)
    con = sqlite3.connect(folder / "blattwerk.db")
    con.executescript(db.SCHEMA)
    for n in range(3):
        con.execute("INSERT INTO users (email, password) VALUES (?, 'x')", (f"u{n}@example.org",))
    con.execute("INSERT INTO sheets (user_id, title, doc) VALUES (1, 'Blatt', '{}')")
    con.commit()
    con.close()
    upload = folder / "users" / "1" / "uploads" / "1"
    upload.parent.mkdir(parents=True)
    upload.write_bytes(b"a picture")
    return folder


@pytest.fixture
def live(tmp_path):
    return make_live(tmp_path / "work" / "live")


@pytest.fixture
def copy(tmp_path):
    return tmp_path / "work" / NAME


def tree(folder):
    """Every file and folder under `folder`: its kind, size, hash and time of change."""
    found = {}
    for path in sorted(folder.rglob("*")):
        stat = path.lstat()
        content = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        found[str(path.relative_to(folder))] = (
            stat.st_mode,
            stat.st_size,
            content,
            stat.st_mtime_ns,
        )
    return found


def rows(path):
    con = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    try:
        tables = [
            name for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        ]
        return {name: con.execute(f"SELECT * FROM {name}").fetchall() for name in tables}
    finally:
        con.close()


# ── alive.sh ──


def test_alive_passes_on_what_the_probe_says(tmp_path):
    up, calls = run(tmp_path, "alive.sh", "blattwerk")
    assert up.returncode == 0
    assert up.stdout + up.stderr == ""
    assert len(calls) == 1
    assert calls[0].startswith("exec blattwerk /app/.venv/bin/python -c ")
    assert "/api/me" in calls[0]
    assert "401" in calls[0]
    down, _ = run(tmp_path, "alive.sh", "blattwerk", rc_exec=1)
    assert down.returncode != 0
    assert down.stdout + down.stderr == ""


def test_the_probe_wants_the_401_of_a_route_that_reads_the_database(tmp_path, server):
    _, calls = run(tmp_path, "alive.sh", "blattwerk")
    probe = calls[0].split(" -c ", 1)[1]
    port = server.rsplit(":", 1)[1]

    def ask(snippet):
        return subprocess.run([sys.executable, "-c", snippet], capture_output=True).returncode

    assert ask(probe.replace("8000", port)) == 0
    # A 200 is not enough: `/` answers without the database.
    assert ask(probe.replace("8000", port).replace("/api/me", "/")) != 0
    # Nobody listens on port 1.
    assert ask(probe.replace("8000", "1")) != 0


# ── canary.sh start ──


def test_start_runs_the_new_image_on_the_copy_and_nowhere_else(tmp_path, live, copy):
    result, calls = run(tmp_path, "canary.sh", "start", live, copy)
    assert result.returncode == 0, result.stdout + result.stderr
    (line,) = [call for call in calls if call.startswith("run ")]
    words = line.split()
    assert words[-1] == f"{IMAGE}:latest"
    assert words[words.index("--name") + 1] == NAME
    assert words.count("-v") == 1
    assert not any(word.startswith(("--volume", "--mount")) for word in words)
    source, inside = words[words.index("-v") + 1].split(":")
    assert inside == "/data"
    assert Path(source) == copy.resolve()
    assert Path(source) != live.resolve()
    assert live.resolve() not in Path(source).parents
    # Not on the proxy's network, no port, and it does not come back by itself.
    for word in words:
        assert not word.startswith(("--network", "--net", "-p", "--publish", "-P", "--restart"))
    # It waits for the canary, not for the live container.
    assert calls[-1].startswith(f"exec {NAME} ")


def refused(case, work):
    """The live folder and the copy folder of a call that must be refused.

    The live folder bears the canary's name where it can, so the place alone is what refuses.
    """
    live = make_live(work / "a" / NAME)
    if case == "the live folder":
        return live, live
    if case == "a symlink to the live folder":
        link = work / "b" / NAME
        link.parent.mkdir()
        link.symlink_to(live)
        return live, link
    if case == "a folder inside the live folder":
        return live, live / NAME
    if case == "a path that leads back into the live folder":
        return live, work / "a" / "x" / ".." / NAME / NAME
    if case == "a parent of the live folder":
        return make_live(work / NAME / "live"), work / NAME
    if case == "the root":
        return live, "/"
    if case == "empty":
        return live, ""
    if case == "no live folder named":
        (work / NAME).mkdir()
        return "", work / NAME
    assert case == "another name"
    (work / "copy").mkdir()
    (work / "copy" / "file").write_text("stays")
    return live, work / "copy"


@pytest.mark.parametrize("command", ["start", "stop"])
@pytest.mark.parametrize(
    "case",
    [
        "the live folder",
        "a symlink to the live folder",
        "a folder inside the live folder",
        "a path that leads back into the live folder",
        "a parent of the live folder",
        "the root",
        "empty",
        "no live folder named",
        "another name",
    ],
)
def test_canary_refuses_a_copy_folder_that_is_not_its_own(tmp_path, command, case):
    work = tmp_path / "work"
    live, copy = refused(case, work)
    before = tree(work)
    result, calls = run(tmp_path, "canary.sh", command, live, copy)
    assert result.returncode != 0
    assert "::error::" in result.stdout
    assert calls == []
    assert tree(work) == before


def test_start_copies_the_data_and_leaves_live_as_it_was(tmp_path, live, copy):
    (live / ".hidden").write_text("too")
    # Empty, as the app leaves it between two writes.
    (live / "blattwerk.db-journal").write_bytes(b"")
    before, held = tree(live), rows(live / "blattwerk.db")
    result, _ = run(tmp_path, "canary.sh", "start", live, copy)
    assert result.returncode == 0, result.stdout + result.stderr
    assert tree(live) == before
    assert rows(copy / "blattwerk.db") == held
    assert len(held["users"]) == 3
    assert (copy / "users" / "1" / "uploads" / "1").read_bytes() == b"a picture"
    assert (copy / ".hidden").read_text() == "too"
    # The database comes through SQLite's backup alone: a journal of live is not the copy's.
    assert sorted(path.name for path in copy.iterdir()) == [".hidden", "blattwerk.db", "users"]
    assert copy.stat().st_mode & 0o777 == 0o700


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes anywhere")
def test_start_opens_the_live_database_read_only(tmp_path, live, copy):
    held = rows(live / "blattwerk.db")
    (live / "blattwerk.db").chmod(0o444)
    live.chmod(0o555)
    try:
        result, _ = run(tmp_path, "canary.sh", "start", live, copy)
    finally:
        live.chmod(0o755)
        (live / "blattwerk.db").chmod(0o644)
    assert result.returncode == 0, result.stdout + result.stderr
    assert rows(copy / "blattwerk.db") == held


def test_start_without_a_database_runs_on_the_empty_copy(tmp_path, live, copy):
    (live / "blattwerk.db").unlink()
    result, calls = run(tmp_path, "canary.sh", "start", live, copy)
    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(path.name for path in copy.iterdir()) == ["users"]
    assert any(call.startswith("run ") for call in calls)


def test_start_clears_what_a_killed_run_left(tmp_path, live, copy):
    (copy / "users" / "9").mkdir(parents=True)
    (copy / "users" / "9" / "old").write_text("left over")
    (copy / "blattwerk.db").write_bytes(b"half a copy")
    result, calls = run(tmp_path, "canary.sh", "start", live, copy)
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls[0] == f"rm -f {NAME}"
    assert calls[1].startswith("run ")
    assert not (copy / "users" / "9").exists()
    assert rows(copy / "blattwerk.db") == rows(live / "blattwerk.db")


def test_start_fails_when_the_canary_never_answers_and_prints_no_logs(tmp_path, live, copy):
    result, calls = run(tmp_path, "canary.sh", "start", live, copy, rc_exec=1)
    assert result.returncode == 1
    (error,) = [line for line in result.stdout.splitlines() if line.startswith("::error::")]
    assert "the canary did not answer" in error
    assert error.endswith(f"docker logs {NAME}")
    assert not any(call.startswith("logs") for call in calls)
    # The job's `always()` step removes the container and the copy.
    assert copy.exists()


def test_start_names_no_path_and_no_file(tmp_path, live, copy):
    """The job log is public."""
    passed, _ = run(tmp_path, "canary.sh", "start", live, copy)
    assert passed.stdout == "the canary answers\n"
    assert passed.stderr == ""
    (live / "blattwerk.db").write_bytes(b"not a database, not at all" * 100)
    failed, calls = run(tmp_path, "canary.sh", "start", live, copy)
    assert failed.returncode == 1
    assert "::error::canary: the copy of the database failed" in failed.stdout
    assert not any(call.startswith("run ") for call in calls)
    for text in (passed.stdout, failed.stdout + failed.stderr):
        assert str(tmp_path) not in text
        assert "uploads" not in text


# ── canary.sh smoke ──


@pytest.mark.parametrize("answer", [0, 1])
def test_smoke_hands_the_invite_over_in_the_environment(tmp_path, answer):
    result, calls = run(tmp_path, "canary.sh", "smoke", rc_smoke=answer)
    assert result.returncode == answer
    assert calls == [
        f"exec {NAME} /app/.venv/bin/python -m blattwerk invite",
        f"exec -i -e SMOKE_INVITE {NAME} /app/.venv/bin/python - http://127.0.0.1:8000",
    ]
    log = tmp_path / "docker.log"
    assert log.with_name("docker.log.invite").read_text() == "/einladung/tok123\n"
    assert log.with_name("docker.log.stdin").read_text() == SMOKE
    assert "tok123" not in "\n".join(calls)
    assert "tok123" not in result.stdout + result.stderr
    assert "smoke ran" in result.stdout


def test_smoke_fails_without_an_invite(tmp_path):
    result, calls = run(tmp_path, "canary.sh", "smoke", rc_invite=1)
    assert result.returncode == 1
    assert "::error::" in result.stdout
    assert "tok123" not in result.stdout + result.stderr
    assert len(calls) == 1


# ── canary.sh stop ──


def test_stop_removes_the_canary_and_the_copy(tmp_path, live, copy):
    assert run(tmp_path, "canary.sh", "start", live, copy)[0].returncode == 0
    before = tree(live)
    result, calls = run(tmp_path, "canary.sh", "stop", live, copy)
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls == [f"rm -f {NAME}"]
    assert not copy.exists()
    assert tree(live) == before


def test_stop_is_fine_when_nothing_is_there(tmp_path, live, copy):
    # docker says 1 when there is no such container.
    result, calls = run(tmp_path, "canary.sh", "stop", live, copy, rc_rm=1)
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls == [f"rm -f {NAME}"]
    assert result.stdout + result.stderr == ""


# ── go-back.sh ──


def test_go_back_puts_prev_in_place_and_points_at_the_readme(tmp_path):
    result, calls = run(tmp_path, "go-back.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls[:3] == [
        f"image inspect {IMAGE}:prev",
        f"tag {IMAGE}:prev {IMAGE}:latest",
        "compose up -d --no-build",
    ]
    assert all(call.startswith("exec blattwerk ") for call in calls[3:])
    (error,) = [line for line in result.stdout.splitlines() if line.startswith("::error::")]
    assert "went back to the prev image" in error
    assert "schema" in error
    assert 'README, "Going back"' in error


def test_go_back_without_prev_changes_nothing(tmp_path):
    result, calls = run(tmp_path, "go-back.sh", rc_image=1)
    assert result.returncode == 1
    assert "::error::no prev image" in result.stdout
    assert calls == [f"image inspect {IMAGE}:prev"]


def test_go_back_fails_when_prev_does_not_answer(tmp_path):
    result, calls = run(tmp_path, "go-back.sh", rc_exec=1)
    assert result.returncode == 1
    assert "compose up -d --no-build" in calls
    assert "::error::the prev image does not answer either" in result.stdout


# ── deploy.yml ──


def code(text):
    """The file without its comments."""
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def steps():
    """Each named step of the deploy: its name and its lines, in the file's order."""
    found = re.split(r"^      - name: (.+)\n", code(DEPLOY) + "\n", flags=re.M)
    return dict(zip(found[1::2], found[2::2], strict=True))


def test_deploy_tries_the_canary_before_it_touches_live():
    assert list(steps()) == [
        "Build image",
        "Start the canary on a copy of the data",
        "Smoke test the canary",
        "Remove the canary and the copy",
        "Snapshot the database",
        "Keep the running image as prev",
        "Deploy",
        "Wait for the app to answer",
        "Smoke test live, read only",
        "Go back to prev",
        "Clean up old images",
    ]
    step = steps()
    assert "run: bash scripts/canary.sh start " in step["Start the canary on a copy of the data"]
    assert "run: bash scripts/canary.sh smoke\n" in step["Smoke test the canary"]
    assert "run: bash scripts/canary.sh stop " in step["Remove the canary and the copy"]
    assert "run: bash scripts/keep-prev.sh\n" in step["Keep the running image as prev"]
    assert "run: docker compose up -d\n" in step["Deploy"]
    assert "if bash scripts/alive.sh blattwerk; then" in step["Wait for the app to answer"]
    assert "continue-on-error" not in DEPLOY


def test_the_build_has_an_end():
    build = steps()["Build image"]
    assert "run: docker compose build\n" in build
    (limit,) = map(int, re.findall(r"^        timeout-minutes: (\d+)$", build, re.M))
    assert 0 < limit <= 30


def test_only_the_cleanup_and_the_way_back_run_after_a_fail():
    """A plain step is skipped after a failed one, so a failed canary means no deploy."""
    conditions = {
        name: re.findall(r"^        if: (.+)$", text, re.M) for name, text in steps().items()
    }
    assert {name: found for name, found in conditions.items() if found} == {
        "Remove the canary and the copy": ["always()"],
        "Go back to prev": ["failure() && steps.up.outcome != 'skipped'"],
    }
    assert "        id: up\n" in steps()["Deploy"]
    assert len(re.findall(r"^        id: ", code(DEPLOY), re.M)) == 1
    assert "run: bash scripts/go-back.sh\n" in steps()["Go back to prev"]


def test_the_live_smoke_test_is_the_read_only_half():
    live = steps()["Smoke test live, read only"]
    (line,) = re.findall(r"^        run: (.+)$", live, re.M)
    call = "docker exec -i blattwerk /app/.venv/bin/python - --read-only http://127.0.0.1:8000"
    assert line == f"{call} < scripts/smoke.py"
    # The invite makes a user: canary.sh does that, and deploy.yml gives it no way to the live app.
    assert "SMOKE_INVITE" not in code(DEPLOY)
    assert "invite" not in code(DEPLOY)
    assert code(DEPLOY).count("--read-only") == 1


def test_deploy_and_compose_name_the_same_data_folder():
    """A folder moved in one file only would snapshot nothing, or try the canary on no data."""
    (mounted,) = re.findall(r"^ +- (\S+):/data$", COMPOSE, re.M)
    (snapshot,) = re.findall(r"scripts/snapshot\.py (\S+)/blattwerk\.db ", code(DEPLOY))
    assert snapshot == mounted
    canary = re.findall(r"scripts/canary\.sh (start|stop) (\S+) (\S+)$", code(DEPLOY), re.M)
    assert [command for command, _, _ in canary] == ["start", "stop"]
    for _, live, copy in canary:
        assert live == mounted
        assert copy == f"{mounted}-canary"


# ── every script ──


@pytest.mark.parametrize("script", sorted(path.name for path in (ROOT / "scripts").glob("*.sh")))
def test_script_parses(script):
    result = subprocess.run(
        ["bash", "-n", str(ROOT / "scripts" / script)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
