"""The deploy's canary and its way back: alive.sh, canary.sh, keep-prev.sh, go-back.sh and
same-image.sh, their place in deploy.sh, and what deploy.yml sends to the VPS. The scripts run
against a docker that only writes down what it was asked.
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
DEPLOY = (ROOT / "scripts" / "deploy.sh").read_text()
SAME_IMAGE_SH = (ROOT / "scripts" / "same-image.sh").read_text()
WORKFLOW = (ROOT / ".github" / "workflows" / "deploy.yml").read_text()
COMPOSE = (ROOT / "docker-compose.yml").read_text()
NAME = "blattwerk-canary"
IMAGE = "blattwerk-blattwerk"
SMOKE = "print('the smoke test')\n"

# RC_<SUBCOMMAND> sets what a call answers: RC_EXEC for alive.sh, RC_IMAGE for `image inspect`.
# ID_PREV and ID_RUNNING are the ids of the `prev` image and of the running container's image.
DOCKER = """#!/usr/bin/env bash
echo "$*" >> "$DOCKER_LOG"
case "$*" in
  "image inspect -f {{.Id}} "*) echo "${ID_PREV:-sha256:prev}" ;;
  "inspect -f {{.Image}} blattwerk") echo "${ID_RUNNING:-sha256:running}" ;;
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
    # The name deploy.sh gave the pulled image, never `latest`: that one runs live.
    assert words[-1] == f"{IMAGE}:canary"
    assert f"{IMAGE}:latest" not in (ROOT / "scripts" / "canary.sh").read_text()
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
    # The stop that follows removes the container at once, so its logs are no hint to give.
    assert "docker logs" not in error
    assert error.endswith(f"docker run --rm {IMAGE}:canary")
    assert not any(call.startswith("logs") for call in calls)
    # The stop that follows removes the container and the copy.
    assert copy.exists()


def test_start_leaves_a_hot_journal_alone_and_says_what_to_do(tmp_path, live, copy):
    """Read-only for real: a journal the app left in the middle of a write stays for the app."""
    crash = (
        "import os, sqlite3, sys\n"
        "con = sqlite3.connect(sys.argv[1], isolation_level=None)\n"
        "con.execute('PRAGMA cache_size = 1')\n"
        "con.execute('BEGIN')\n"
        "for n in range(200):\n"
        "    doc = ('d' * 4000,)\n"
        "    con.execute(\"INSERT INTO sheets (user_id, title, doc) VALUES (1, 'x', ?)\", doc)\n"
        "os._exit(0)\n"
    )
    subprocess.run([sys.executable, "-c", crash, str(live / "blattwerk.db")], check=True)
    assert (live / "blattwerk.db-journal").read_bytes()
    before = tree(live)
    result, calls = run(tmp_path, "canary.sh", "start", live, copy)
    assert result.returncode == 1
    assert "::error::canary: the copy of the database failed" in result.stdout
    assert "Open the site once and sign in, so the app mends it, then rerun." in result.stdout
    assert not any(call.startswith("run ") for call in calls)
    assert tree(live) == before


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


@pytest.mark.skipif(os.geteuid() == 0, reason="root deletes anywhere")
def test_stop_that_cannot_delete_the_copy_fails_and_names_no_file(tmp_path, live, copy):
    assert run(tmp_path, "canary.sh", "start", live, copy)[0].returncode == 0
    locked = copy / "users" / "1" / "uploads"
    locked.chmod(0o500)
    try:
        result, _ = run(tmp_path, "canary.sh", "stop", live, copy)
    finally:
        locked.chmod(0o700)
    assert result.returncode == 1
    assert "::error::" in result.stdout
    assert "uploads" not in result.stdout + result.stderr
    assert str(copy) not in result.stdout + result.stderr


def test_stop_is_fine_when_nothing_is_there(tmp_path, live, copy):
    # docker says 1 when there is no such container.
    result, calls = run(tmp_path, "canary.sh", "stop", live, copy, rc_rm=1)
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls == [f"rm -f {NAME}"]
    assert result.stdout + result.stderr == ""


# ── go-back.sh ──


ASK_PREV = f"image inspect -f {{{{.Id}}}} {IMAGE}:prev"
ASK_RUNNING = "inspect -f {{.Image}} blattwerk"
WENT_BACK = [f"tag {IMAGE}:prev {IMAGE}:latest", "compose up -d --no-build"]


def test_go_back_by_hand_puts_prev_in_place_and_points_at_the_readme(tmp_path):
    """By hand: neither PREV_KEPT nor PREV_IMAGE is set."""
    result, calls = run(tmp_path, "go-back.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls[:4] == [ASK_PREV, ASK_RUNNING, *WENT_BACK]
    assert calls[4:]
    assert all(call.startswith("exec blattwerk ") for call in calls[4:])
    (error,) = [line for line in result.stdout.splitlines() if line.startswith("::error::")]
    assert "went back to the prev image" in error
    assert "schema" in error
    assert 'README, "Going back"' in error
    assert result.stdout.endswith("blattwerk answers on the prev image\n")


def test_go_back_without_prev_changes_nothing(tmp_path):
    result, calls = run(tmp_path, "go-back.sh", rc_image=1)
    assert result.returncode == 1
    assert "::error::no prev image" in result.stdout
    assert calls == [ASK_PREV]


def test_go_back_leaves_a_prev_alone_that_this_deploy_did_not_tag(tmp_path):
    result, calls = run(tmp_path, "go-back.sh", prev_kept="")
    assert result.returncode == 1
    assert "::error::prev is not the image that ran before this deploy" in result.stdout
    assert calls == [ASK_PREV]
    # The deploy hands over what keep-prev.sh said.
    assert "PREV_KEPT=$(sed -n 's/^kept=//p' \"$GITHUB_OUTPUT\") \\" in lines()


def test_go_back_goes_back_after_keep_prev_tagged(tmp_path):
    result, calls = run(
        tmp_path, "go-back.sh", prev_kept="yes", prev_image="sha256:old", id_prev="sha256:old"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls[:4] == [ASK_PREV, ASK_RUNNING, *WENT_BACK]


def test_keep_prev_writes_down_the_id_it_tagged(tmp_path):
    output = tmp_path / "output"
    result, calls = run(tmp_path, "keep-prev.sh", github_output=output, id_running="sha256:abc123")
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls[-1] == f"tag sha256:abc123 {IMAGE}:prev"
    assert output.read_text() == "kept=yes\nimage=sha256:abc123\n"
    assert result.stdout == "prev is abc123\n"
    # The deploy hands the id over.
    assert "PREV_IMAGE=$(sed -n 's/^image=//p' \"$GITHUB_OUTPUT\") \\" in lines()
    # And keep-prev.sh writes where the deploy reads.
    assert at("export GITHUB_OUTPUT=$work/output") < at(STEPS[0])


def test_keep_prev_goes_on_and_writes_nothing_down_when_the_tag_fails(tmp_path):
    """An image with no name left cannot be tagged, and the deploy must go on all the same."""
    output = tmp_path / "output"
    result, calls = run(tmp_path, "keep-prev.sh", github_output=output, rc_tag=1)
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls[-1].startswith("tag ")
    assert "::warning::the running image has no name left" in result.stdout
    assert not output.exists()


def test_go_back_leaves_a_prev_alone_that_is_not_the_id_keep_prev_wrote_down(tmp_path):
    result, calls = run(
        tmp_path, "go-back.sh", prev_kept="yes", prev_image="sha256:old", id_prev="sha256:older"
    )
    assert result.returncode == 1
    (error,) = [line for line in result.stdout.splitlines() if line.startswith("::error::")]
    assert "prev is not the image that ran before this deploy" in error
    assert "nothing was changed" in error
    assert "went back" not in result.stdout
    assert calls == [ASK_PREV]


def test_go_back_says_so_when_prev_is_the_image_that_already_runs(tmp_path):
    """A rerun with a cached build: the build is the image that ran, and prev names it too."""
    result, calls = run(
        tmp_path,
        "go-back.sh",
        prev_kept="yes",
        prev_image="sha256:same",
        id_prev="sha256:same",
        id_running="sha256:same",
    )
    assert result.returncode == 1
    (error,) = [line for line in result.stdout.splitlines() if line.startswith("::error::")]
    assert "prev is the image that already runs" in error
    assert "nothing older to go back to" in error
    assert "went back" not in result.stdout
    # No `up`: the container stays. `latest` names what runs again, whatever the deploy made of it.
    assert calls == [ASK_PREV, ASK_RUNNING, WENT_BACK[0]]


def test_go_back_goes_back_when_no_container_is_there(tmp_path):
    result, calls = run(tmp_path, "go-back.sh", rc_inspect=1, id_running="sha256:prev")
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls[:4] == [ASK_PREV, ASK_RUNNING, *WENT_BACK]


@pytest.mark.parametrize(
    "answers",
    [
        {},
        {"rc_image": 1},
        {"prev_kept": ""},
        {"prev_image": "sha256:old"},
        {"id_running": "sha256:prev"},
        {"rc_exec": 1},
    ],
)
def test_go_back_names_no_path(tmp_path, answers):
    """The job log is public."""
    result, _ = run(tmp_path, "go-back.sh", **answers)
    text = result.stdout + result.stderr
    assert str(tmp_path) not in text
    assert "/home" not in text
    assert "/data" not in text


def test_go_back_fails_when_prev_does_not_answer(tmp_path):
    result, calls = run(tmp_path, "go-back.sh", rc_exec=1)
    assert result.returncode == 1
    assert "compose up -d --no-build" in calls
    assert "::error::the prev image does not answer either" in result.stdout


# ── deploy.sh ──


def code(text):
    """The file without its comments."""
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def lines():
    """The lines of deploy.sh that do something, without their indent."""
    return [line.strip() for line in code(DEPLOY).splitlines() if line.strip()]


def at(start):
    """Where the one line of deploy.sh stands that begins so."""
    (found,) = [n for n, line in enumerate(lines()) if line.startswith(start)]
    return found


STEPS = [
    'timeout 2m bash "$work/keep-prev.sh"',
    'timeout 15m docker pull -q "$image:$sha"',
    f'docker tag "$image:$sha" {IMAGE}:canary',
    'timeout 3m bash "$work/canary.sh" start "$live" "$copy" &&',
    'timeout 5m bash "$work/canary.sh" smoke || passed=no',
    'timeout 2m bash "$work/canary.sh" stop "$live" "$copy"',
    "[[ $passed == yes ]] || exit 1",
    'timeout 3m python3 "$work/snapshot.py" "$live/blattwerk.db" "$backups" "$sha"',
    "promoted=yes",
    f"docker tag {IMAGE}:canary {IMAGE}:latest",
    "timeout 3m docker compose up -d --no-build",
    'timeout 1m bash "$work/same-image.sh"',
    'if bash "$work/alive.sh" blattwerk; then',
    "timeout 2m docker exec -i blattwerk /app/.venv/bin/python - --read-only",
    "docker image prune -f",
]


def test_deploy_tries_the_canary_before_it_touches_live():
    found = [at(step) for step in STEPS]
    assert found == sorted(found)
    assert "set -euo pipefail" in lines()
    # keep-prev is the first thing the script runs.
    assert at(STEPS[0]) == at("trap finish EXIT") + 1
    # The canary goes pass or fail: a failed start or smoke test is only written down, and ends
    # the run once the stop has run.
    start, smoke, stop, passed = (at(step) for step in STEPS[3:7])
    assert [smoke, stop, passed] == [start + 1, start + 2, start + 3]
    assert "continue-on-error" not in WORKFLOW


def test_latest_moves_only_once_the_canary_passed():
    """After a failed canary `latest` still names the image that runs."""
    promote = f"docker tag {IMAGE}:canary {IMAGE}:latest"
    assert at("[[ $passed == yes ]] || exit 1") < at(promote)
    # Nothing else in the deploy builds, names `latest` or starts the container.
    assert "compose build" not in code(DEPLOY)
    assert "--build" not in code(DEPLOY)
    assert "docker build" not in code(DEPLOY)
    assert [line for line in lines() if "compose up" in line] == [
        "timeout 3m docker compose up -d --no-build"
    ]
    assert code(DEPLOY).count(f"{IMAGE}:latest") == 1
    assert [line for line in lines() if "docker tag" in line] == [
        f'docker tag "$image:$sha" {IMAGE}:canary',
        promote,
    ]
    assert f"{IMAGE}:latest" not in SAME_IMAGE_SH


LAYERS = '["sha256:base","sha256:app"]'
CONFIG = '{"Cmd":["serve"],"Env":["KEY=hushhush"]}'

# Answers by what it is asked: the container's image id, then the layers and the config of that
# id and of the `canary` name. An empty answer stands for a container or an image that is not
# there: docker says so on stderr and fails.
SAME_IMAGE = """#!/usr/bin/env bash
case "$*" in
  # An image with no name at all: the container's id came back empty.
  *" ") answer= ;;
  "inspect -f {{.Image}} blattwerk") answer=$ID_RUNNING ;;
  "image inspect -f {{json .RootFS.Layers}} $ID_RUNNING") answer=$LAYERS_RUNNING ;;
  "image inspect -f {{json .Config}} $ID_RUNNING") answer=$CONFIG_RUNNING ;;
  "image inspect -f {{json .RootFS.Layers}} blattwerk-blattwerk:canary") answer=$LAYERS_CANARY ;;
  "image inspect -f {{json .Config}} blattwerk-blattwerk:canary") answer=$CONFIG_CANARY ;;
  *) answer= ;;
esac
if [ -z "$answer" ]; then
  echo "Error response from daemon: no such object: $*" >&2
  exit 1
fi
echo "$answer"
"""


def same_image(tmp_path, **answers):
    """Runs same-image.sh as the deploy does against a docker that answers so."""
    stub = tmp_path / "docker"
    stub.write_text(SAME_IMAGE)
    stub.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "ID_RUNNING": "sha256:old",
        "LAYERS_RUNNING": LAYERS,
        "CONFIG_RUNNING": CONFIG,
        "LAYERS_CANARY": LAYERS,
        "CONFIG_CANARY": CONFIG,
        **{key.upper(): value for key, value in answers.items()},
    }
    command = ["bash", str(ROOT / "scripts" / "same-image.sh")]
    done = subprocess.run(command, env=env, capture_output=True, text=True)
    # The config holds env values, and the job log is public.
    assert "hushhush" not in done.stdout + done.stderr
    return done


@pytest.mark.parametrize("running", ["sha256:canary", "sha256:old"], ids=["same id", "other id"])
def test_a_container_with_the_layers_and_config_the_canary_tried_passes(tmp_path, running):
    """A build out of the cache has a new id for the same image, and compose keeps the container."""
    done = same_image(tmp_path, id_running=running)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "::error::" not in done.stdout
    assert running in done.stdout


@pytest.mark.parametrize(
    "answers",
    [
        pytest.param({"layers_running": '["sha256:base","sha256:older"]'}, id="other layers"),
        # A new `ENV` or `CMD` in the Dockerfile adds no layer.
        pytest.param({"config_running": '{"Cmd":["other"]}'}, id="other config"),
        pytest.param({"id_running": ""}, id="no container"),
        pytest.param({"layers_running": "", "config_running": ""}, id="no image of that id"),
        pytest.param({"layers_canary": "", "config_canary": ""}, id="no canary image"),
        # Two inspects that fail give two empty answers, which are not the same image.
        pytest.param(
            {"id_running": "", "layers_canary": "", "config_canary": ""}, id="nothing there"
        ),
        pytest.param({"config_running": "", "config_canary": ""}, id="no config to read"),
    ],
)
def test_a_container_that_kept_the_old_image_fails_the_deploy(tmp_path, answers):
    done = same_image(tmp_path, **answers)
    assert done.returncode == 1, done.stdout + done.stderr
    assert "::error::the blattwerk container does not run the image the canary tried" in done.stdout


def test_every_step_has_an_end_and_the_job_ends_after_them_all():
    """The job's limit must not end the run between `up` and the way back."""
    limits = {}
    for line in lines():
        # A script, the pull, `up` or the live smoke test. One try of alive.sh ends by itself.
        if not re.search(r'(bash|python3) "\$work/|docker (pull|compose|exec) ', line):
            continue
        if 'bash "$work/alive.sh"' in line:
            continue
        (limits[line],) = map(int, re.findall(r"^timeout (\d+)m ", line))
    assert len(limits) == 10
    assert all(limit > 0 for limit in limits.values())
    # go-back.sh waits a minute for the app, after an `up`.
    (back,) = [limit for line, limit in limits.items() if "go-back.sh" in line]
    assert back >= 2
    # The wait for the app: 30 tries, 2 s apart, and a try gives up after 2 s.
    assert "for _ in $(seq 1 30); do" in lines()
    assert "timeout=2" in (ROOT / "scripts" / "alive.sh").read_text()
    (job,) = map(int, re.findall(r"^    timeout-minutes: (\d+)$", jobs()["deploy"], re.M))
    # Room for that wait and for the lines without a limit: tag, rmi, the read of smoke.py, prune.
    assert sum(limits.values()) + 5 <= job


def test_only_the_way_back_runs_after_a_fail():
    """A failed line ends the script, so a failed canary means no deploy."""
    assert [line for line in lines() if line.startswith("trap ")] == [
        "trap - EXIT",
        "trap finish EXIT",
    ]
    # From the tag step on, not from `up` on: `latest` has moved by then. Not before it: the old
    # container is untouched and there is nothing to go back from.
    assert [line for line in lines() if line.startswith("promoted=")] == [
        "promoted=",
        "promoted=yes",
    ]
    assert at("promoted=yes") == at(f"docker tag {IMAGE}:canary {IMAGE}:latest") - 1
    assert "if [[ $status != 0 && -n $promoted ]]; then" in lines()
    (back,) = [line for line in lines() if "go-back.sh" in line and not line.startswith("cp ")]
    # A way back that fails must not hide the status of the deploy.
    assert back == 'timeout 3m bash "$work/go-back.sh" || true'
    assert at("if [[ $status != 0") < at(back) < at('exit "$status"') < at("trap finish EXIT")


def test_the_live_smoke_test_is_the_read_only_half():
    (live,) = [line for line in lines() if "--read-only" in line]
    call = "docker exec -i blattwerk /app/.venv/bin/python - --read-only http://127.0.0.1:8000"
    assert live == f'timeout 2m {call} <"$work/smoke.py"'
    # The invite makes a user: canary.sh does that, and deploy.sh gives it no way to the live app.
    assert "SMOKE_INVITE" not in code(DEPLOY)
    assert "invite" not in code(DEPLOY)
    assert code(DEPLOY).count("--read-only") == 1


def test_the_smoke_test_comes_out_of_the_image_it_tests():
    read = f"docker run --rm --network none --entrypoint cat {IMAGE}:canary /app/scripts/smoke.py"
    assert f'if ! {read} >"$work/smoke.py"; then' in lines()
    assert "COPY scripts/smoke.py ./scripts/smoke.py\n" in (ROOT / "Dockerfile").read_text()
    # No copy of it lies beside the scripts on the VPS.
    (copied,) = [line for line in lines() if line.startswith("cp ")]
    assert "smoke.py" not in copied


def test_deploy_and_compose_name_the_same_data_folder():
    """A folder moved in one file only would snapshot nothing, or try the canary on no data."""
    (mounted,) = re.findall(r"^ +- (\S+):/data$", COMPOSE, re.M)
    (live,) = re.findall(r"^live=(\S+)$", code(DEPLOY), re.M)
    (copy,) = re.findall(r"^copy=(\S+)$", code(DEPLOY), re.M)
    assert live == mounted
    assert copy == f"{mounted}-canary"
    (snapshot,) = re.findall(r'snapshot\.py" (\S+)/blattwerk\.db" ', code(DEPLOY))
    assert snapshot == '"$live'
    canary = re.findall(r'canary\.sh" (start|stop) (\S+) (\S+)', code(DEPLOY))
    assert canary == [("start", '"$live"', '"$copy"'), ("stop", '"$live"', '"$copy"')]


# ── deploy.sh, run ──

SHA = "0123456789abcdef0123456789abcdef01234567"
(LIVE,) = re.findall(r"^ +- (\S+):/data$", COMPOSE, re.M)

# Keeps its images as files: a name's file holds the id it stands for, and `runs` the id of the
# image the blattwerk container runs. An id stands for its own layers and config.
REGISTRY = """#!/usr/bin/env bash
echo "$*" >> "$DOCKER_LOG"
id() { if [[ $1 == sha256:* ]]; then echo "$1"; else cat "$STATE/${1##*:}" 2>/dev/null; fi; }
case "$1" in
  pull) echo sha256:new > "$STATE/${3##*:}" ;;
  tag) held=$(id "$2") && echo "$held" > "$STATE/${3##*:}" ;;
  rmi) rm "$STATE/${2##*:}" ;;
  run) echo "print('the smoke test')"; exit "${RC_RUN:-0}" ;;
  compose) cp "$STATE/latest" "$STATE/runs" ;;
  inspect) cat "$STATE/runs" ;;
  image) if [ "$2" = inspect ]; then id "${@: -1}"; fi ;;
  exec) case "$*" in *--read-only*) cat > /dev/null; exit "${RC_LIVE:-0}" ;; esac ;;
esac
"""

# deploy.sh names the live folders itself, so the two scripts that read and write there get a
# stand-in that only writes down how it was called.
CANARY = """#!/usr/bin/env bash
echo "canary.sh $*" >> "$DOCKER_LOG"
if [ "$1" = smoke ]; then
  cat "$(dirname "$0")/smoke.py" > "$DOCKER_LOG.smoke"
  exit "${RC_CANARY:-0}"
fi
"""
SNAPSHOT = """import os, sys
with open(os.environ["DOCKER_LOG"], "a") as log:
    print("snapshot.py", *sys.argv[1:], file=log)
"""

PULLED = [
    "tag sha256:old blattwerk-blattwerk:prev",
    f"pull -q ghcr.io/pgoell/blattwerk:{SHA}",
    f"tag ghcr.io/pgoell/blattwerk:{SHA} {IMAGE}:canary",
    f"rmi ghcr.io/pgoell/blattwerk:{SHA}",
    f"run --rm --network none --entrypoint cat {IMAGE}:canary /app/scripts/smoke.py",
]
TRIED = [
    f"canary.sh start {LIVE} {LIVE}-canary",
    "canary.sh smoke",
    f"canary.sh stop {LIVE} {LIVE}-canary",
]
WENT_LIVE = [
    f"snapshot.py {LIVE}/blattwerk.db {LIVE}-backups {SHA}",
    f"tag {IMAGE}:canary {IMAGE}:latest",
    "compose up -d --no-build",
    "exec -i blattwerk /app/.venv/bin/python - --read-only http://127.0.0.1:8000",
]


def deploy(tmp_path, **answers):
    """Runs deploy.sh from a folder of its own, as it lies on the VPS.

    Gives its result, what it did (the docker calls that only ask are left out) and the id each
    name stands for at the end.
    """
    scripts, state, temp = tmp_path / "scripts", tmp_path / "state", tmp_path / "tmp"
    stub, log = tmp_path / "bin" / "docker", tmp_path / "docker.log"
    for folder in (scripts, state, temp, stub.parent):
        folder.mkdir()
    for name in ("deploy.sh", "alive.sh", "go-back.sh", "keep-prev.sh", "same-image.sh"):
        (scripts / name).write_text((ROOT / "scripts" / name).read_text())
    (scripts / "canary.sh").write_text(CANARY)
    (scripts / "snapshot.py").write_text(SNAPSHOT)
    stub.write_text(REGISTRY)
    stub.chmod(0o755)
    for name in ("latest", "runs"):
        (state / name).write_text("sha256:old\n")
    env = {
        **os.environ,
        "PATH": f"{stub.parent}:{os.environ['PATH']}",
        "DOCKER_LOG": str(log),
        "STATE": str(state),
        "TMPDIR": str(temp),
        "ALIVE_WAIT": "0",
        **{key.upper(): str(value) for key, value in answers.items()},
    }
    command = ["bash", str(scripts / "deploy.sh"), SHA]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60, env=env)
    asks = ("inspect ", "image inspect ", "exec blattwerk ")
    did = [call for call in log.read_text().splitlines() if not call.startswith(asks)]
    # The folder of its own that the script made is gone again, pass or fail.
    assert list(temp.iterdir()) == []
    # The job log is public.
    assert "/home" not in result.stdout + result.stderr
    assert str(tmp_path) not in result.stdout + result.stderr
    return result, did, {path.name: path.read_text().strip() for path in state.iterdir()}


def test_a_deploy_puts_the_image_live_that_the_canary_tried(tmp_path):
    result, did, names = deploy(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert did == [*PULLED, *TRIED, *WENT_LIVE, "image prune -f"]
    # The registry's name is gone again, and `prev` names the image that ran before.
    assert names == {
        "runs": "sha256:new",
        "latest": "sha256:new",
        "canary": "sha256:new",
        "prev": "sha256:old",
    }
    # The canary was fed the smoke test that came out of the image.
    assert (tmp_path / "docker.log.smoke").read_text() == SMOKE
    assert "::error::" not in result.stdout
    assert result.stdout.endswith(f"blattwerk runs {SHA}\n")


def test_a_failed_canary_leaves_latest_and_the_container_as_they_were(tmp_path):
    result, did, names = deploy(tmp_path, rc_canary=1)
    assert result.returncode == 1
    # The canary and the copy go all the same, and nothing after them runs: no way back either.
    assert did == [*PULLED, *TRIED]
    assert names["latest"] == names["runs"] == "sha256:old"
    # The failed image stays for a look.
    assert names["canary"] == "sha256:new"


def test_an_image_without_a_smoke_test_fails_before_the_canary(tmp_path):
    """An image from before the Dockerfile copied scripts/smoke.py into it."""
    result, did, names = deploy(tmp_path, rc_run=1)
    assert result.returncode == 1
    assert "::error::the image holds no /app/scripts/smoke.py" in result.stdout
    assert did == PULLED
    assert names["latest"] == names["runs"] == "sha256:old"


def test_a_failed_live_smoke_test_goes_back_to_prev(tmp_path):
    result, did, names = deploy(tmp_path, rc_live=1)
    # The status of the deploy, not of the way back, which passed.
    assert result.returncode == 1
    # No prune: the failed image stays for a look.
    assert did == [*PULLED, *TRIED, *WENT_LIVE, *WENT_BACK]
    assert names["latest"] == names["runs"] == names["prev"] == "sha256:old"
    assert "::error::the deploy failed and went back to the prev image" in result.stdout
    assert result.stdout.endswith("blattwerk answers on the prev image\n")


# ── deploy.yml ──


def jobs():
    """Each job of the workflow: its name and its lines."""
    found = re.split(r"^  (\w+):\n", code(WORKFLOW).split("\njobs:\n")[1] + "\n", flags=re.M)
    return dict(zip(found[1::2], found[2::2], strict=True))


def test_the_build_has_an_end():
    (limit,) = map(int, re.findall(r"^    timeout-minutes: (\d+)$", jobs()["build"], re.M))
    assert limit == 20


def test_no_job_runs_on_the_vps_and_the_deploy_job_sends_only_the_sha():
    """Nothing of a commit runs on the box but its image."""
    assert list(jobs()) == ["build", "deploy"]
    assert "self-hosted" not in code(WORKFLOW)
    assert "continue-on-error" not in WORKFLOW
    for job in jobs().values():
        assert re.findall(r"^    runs-on: (.+)$", job, re.M) == ["ubuntu-latest"]
    build, deploy = jobs()["build"], jobs()["deploy"]
    sha = "${{ github.event.workflow_run.head_sha }}"
    # The image deploy.sh pulls is the one the build pushed.
    (image,) = re.findall(r"^image=(\S+)$", code(DEPLOY), re.M)
    assert f"          tags: {image}:{sha}\n" in build
    assert f"          ref: {sha}\n" in build
    assert "          persist-credentials: false\n" in build
    # No checkout and no action: the job runs no file of the repo.
    assert "uses:" not in deploy
    assert "scripts/" not in deploy
    assert "    needs: build\n" in deploy
    assert "    environment: vps\n" in deploy
    assert "    permissions: {}\n" in deploy
    assert f"          SHA: {sha}\n" in deploy
    assert re.findall(r"^          ssh .*$", deploy, re.M) == [
        "          ssh -i ~/.ssh/deploy -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes"
        ' "$DEPLOY_HOST" "$SHA"'
    ]
    assert deploy.rstrip().endswith('"$DEPLOY_HOST" "$SHA"')


# ── every script ──


@pytest.mark.parametrize("script", sorted(path.name for path in (ROOT / "scripts").glob("*.sh")))
def test_script_parses(script):
    result = subprocess.run(
        ["bash", "-n", str(ROOT / "scripts" / script)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
