"""The deploy's canary and its way back: alive.sh, canary.sh, keep-prev.sh, go-back.sh and
same-image.sh, their place in deploy.sh, and what deploy.yml sends to the VPS. The scripts run
against a docker that only writes down what it was asked.
"""

# Tests of one behaviour each live in the sibling modules. Shared helpers stay here so existing imports keep working.

import hashlib
import os
import re
import sqlite3
import subprocess
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


# ── go-back.sh ──


ASK_PREV = f"image inspect -f {{{{.Id}}}} {IMAGE}:prev"
ASK_RUNNING = "inspect -f {{.Image}} blattwerk"
WENT_BACK = [f"tag {IMAGE}:prev {IMAGE}:latest", "compose up -d --no-build"]


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
    f"run --rm --init --network none --entrypoint cat {IMAGE}:canary /app/scripts/smoke.py",
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


# ── deploy.yml ──


def jobs():
    """Each job of the workflow: its name and its lines."""
    found = re.split(r"^  (\w+):\n", code(WORKFLOW).split("\njobs:\n")[1] + "\n", flags=re.M)
    return dict(zip(found[1::2], found[2::2], strict=True))
