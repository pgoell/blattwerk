"""The stage: scripts/stage.sh and scripts/stage-teacher.py. The image that runs live, on a copy of
the live data, for a session that only uses the app.

stage.sh runs against a docker and an ss that only write down what they were asked, and HOME is a
tmp folder: no test here starts a container or comes near the real data.
"""

import os
import socket
import subprocess
import sys
from http.cookies import SimpleCookie
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from playwright.sync_api import expect
from test_canary import ROOT, make_live, rows, tree
from ui import BROWSER, PASSWORD, TEXT, box, sheet, upload, user

from blattwerk import auth, db

NAME = "blattwerk-stage"
IMAGE = "blattwerk-blattwerk:latest"
EMAIL = "teacher-run@stage.invalid"
TEACHER = ROOT / "scripts" / "stage-teacher.py"
INVITE = f"exec {NAME} /app/.venv/bin/python -m blattwerk invite"
SIGN_UP = f"exec -i -e STAGE_INVITE {NAME} /app/.venv/bin/python - http://127.0.0.1:8000"
LOGIN = ["URL: http://127.0.0.1:8220", f"E-Mail: {EMAIL}", "Passwort: geheim-aus-dem-stub"]
TAKEN = "LISTEN 0 4096 127.0.0.1:8220 0.0.0.0:*"

# RC_<SUBCOMMAND> sets what a call answers: RC_EXEC for alive.sh, RC_IMAGE for `image inspect`.
DOCKER = """#!/usr/bin/env bash
echo "$*" >> "$DOCKER_LOG"
case "$*" in
  *"blattwerk invite"*) echo /einladung/tok123; exit "${RC_INVITE:-0}" ;;
  *"-e STAGE_INVITE"*)
    printenv STAGE_INVITE > "$DOCKER_LOG.invite"
    cat > "$DOCKER_LOG.stdin"
    echo "E-Mail: teacher-run@stage.invalid"
    echo "Passwort: geheim-aus-dem-stub"
    exit "${RC_SIGNUP:-0}" ;;
esac
rc=RC_${1^^}
exit "${!rc:-0}"
"""

# Writes its words down, one a line, and answers with $SS: the lines of the sockets that listen.
SS = """#!/usr/bin/env bash
printf '%s\\n' "$@" > "$DOCKER_LOG.ss"
printf '%s' "${SS:-}"
"""


def run(tmp_path, *args, **answers):
    """Runs stage.sh with HOME in the tmp folder, gives its result and the docker calls it made."""
    stubs, log = tmp_path / "bin", tmp_path / "docker.log"
    if not stubs.exists():
        stubs.mkdir()
        for stub, text in (("docker", DOCKER), ("ss", SS)):
            (stubs / stub).write_text(text)
            (stubs / stub).chmod(0o755)
    log.unlink(missing_ok=True)
    env = {
        **os.environ,
        "HOME": str(tmp_path / "home"),
        "PATH": f"{stubs}:{os.environ['PATH']}",
        "DOCKER_LOG": str(log),
        "ALIVE_WAIT": "0",
        **{key.upper(): str(value) for key, value in answers.items()},
    }
    env.pop("STAGE_INVITE", None)
    command = ["bash", str(ROOT / "scripts" / "stage.sh"), *map(str, args)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=20, env=env)
    return result, log.read_text().splitlines() if log.exists() else []


@pytest.fixture
def share(tmp_path):
    """~/.local/share of the tmp HOME, with a live folder and a backup."""
    share = tmp_path / "home" / ".local" / "share"
    make_live(share / "blattwerk")
    (share / "blattwerk-backups").mkdir()
    (share / "blattwerk-backups" / "pre-abc.db").write_bytes(b"a snapshot")
    return share


@pytest.fixture
def live(share):
    return share / "blattwerk"


@pytest.fixture
def copy(share):
    return share / NAME


def up(tmp_path):
    result, calls = run(tmp_path, "up")
    assert result.returncode == 0, result.stdout + result.stderr
    return result, calls


# ── stage.sh up ──


def test_a1_up_runs_the_live_image_on_the_copy_and_never_on_the_live_folder(tmp_path, live, copy):
    _, calls = up(tmp_path)
    (line,) = [call for call in calls if call.startswith("run ")]
    words = line.split()
    assert words[-1] == IMAGE
    assert words[words.index("--name") + 1] == NAME
    assert words.count("-v") == 1
    assert not any(word.startswith(("--volume", "--mount")) for word in words)
    source, inside = words[words.index("-v") + 1].split(":")
    assert inside == "/data"
    assert Path(source) == copy.resolve()
    assert Path(source) != live.resolve()
    assert live.resolve() not in Path(source).parents
    # Every other call names the stage too, never the live container.
    assert all(NAME in call.split() or call == f"image inspect {IMAGE}" for call in calls)


def test_a2_the_only_port_is_local_with_no_network_and_no_restart(tmp_path, share):
    _, calls = up(tmp_path)
    (line,) = [call for call in calls if call.startswith("run ")]
    words = line.split()
    assert words.count("-p") == 1
    assert words[words.index("-p") + 1] == "127.0.0.1:8220:8000"
    for word in words:
        assert not word.startswith(("--network", "--net", "--publish", "-P", "--restart"))


def test_a3_up_and_down_leave_the_live_folder_and_the_backups_as_they_were(tmp_path, share, copy):
    live, backups = share / "blattwerk", share / "blattwerk-backups"
    (live / ".hidden").write_text("too")
    # Empty, as the app leaves it between two writes.
    (live / "blattwerk.db-journal").write_bytes(b"")
    before, held = (tree(live), tree(backups)), rows(live / "blattwerk.db")
    up(tmp_path)
    assert (tree(live), tree(backups)) == before
    assert rows(copy / "blattwerk.db") == held
    assert len(held["users"]) == 3
    assert (copy / "users" / "1" / "uploads" / "1").read_bytes() == b"a picture"
    # The database comes through SQLite's backup alone: a journal of live is not the copy's.
    assert sorted(path.name for path in copy.iterdir()) == [".hidden", "blattwerk.db", "users"]
    assert run(tmp_path, "down")[0].returncode == 0
    assert (tree(live), tree(backups)) == before


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes anywhere")
def test_a3_up_needs_no_write_in_the_live_folder(tmp_path, live, copy):
    held = rows(live / "blattwerk.db")
    folders = [live, *(path for path in live.rglob("*") if path.is_dir())]
    files = [path for path in live.rglob("*") if path.is_file()]
    for path in files:
        path.chmod(0o400)
    for path in folders:
        path.chmod(0o500)
    before = tree(live)
    try:
        result, _ = run(tmp_path, "up")
        after = tree(live)
    finally:
        # The copy took the modes along. Both get theirs back, so the tmp folder can go.
        for path in [*folders, *(p for p in copy.rglob("*") if p.is_dir())]:
            path.chmod(0o700)
    assert result.returncode == 0, result.stdout + result.stderr
    assert after == before
    assert rows(copy / "blattwerk.db") == held


def test_a5_up_makes_a_teacher_who_is_no_admin_and_prints_the_login_last(tmp_path, live, copy):
    before = tree(live)
    result, calls = up(tmp_path)
    assert result.stdout.splitlines()[-3:] == LOGIN
    assert calls[-2:] == [INVITE, SIGN_UP]
    assert "--admin" not in " ".join(calls)
    # In the copy only: both calls go into the stage's container, and live is as it was.
    assert tree(live) == before
    # The invite is a secret: in the environment, on no command line and in no output.
    log = tmp_path / "docker.log"
    assert log.with_name("docker.log.invite").read_text() == "/einladung/tok123\n"
    assert log.with_name("docker.log.stdin").read_text() == TEACHER.read_text()
    assert "tok123" not in "\n".join(calls)
    assert "tok123" not in result.stdout + result.stderr


def test_a7_up_twice_in_a_row_starts_from_a_fresh_copy(tmp_path, live, copy):
    up(tmp_path)
    (copy / "users" / "9").mkdir()
    (copy / "users" / "9" / "old").write_text("left over")
    result, calls = up(tmp_path)
    assert calls[0] == f"rm -f {NAME}"
    assert [call.split()[0] for call in calls].index("run") > 0
    assert not (copy / "users" / "9").exists()
    assert rows(copy / "blattwerk.db") == rows(live / "blattwerk.db")
    assert result.stdout.splitlines()[-3:] == LOGIN


def test_i4_the_copy_is_for_its_owner_alone(tmp_path, share, copy):
    up(tmp_path)
    assert copy.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize(
    "case", ["the database copy", "docker run", "the container", "the invite", "the sign-up"]
)
def test_i2_an_up_that_fails_half_way_leaves_no_container_and_no_copy(tmp_path, live, copy, case):
    answers = {
        "the database copy": {},
        "docker run": {"rc_run": 1},
        "the container": {"rc_exec": 1},
        "the invite": {"rc_invite": 1},
        "the sign-up": {"rc_signup": 1},
    }[case]
    if case == "the database copy":
        (live / "blattwerk.db").write_bytes(b"not a database")
    before = tree(live)
    result, calls = run(tmp_path, "up", **answers)
    assert result.returncode != 0
    assert "stage: " in result.stderr
    assert not copy.exists()
    # The last word to docker takes the container away.
    assert calls[-1] == f"rm -f {NAME}"
    assert any(call.startswith("run ") for call in calls) == (case != "the database copy")
    assert "Passwort" not in result.stdout
    assert tree(live) == before


@pytest.mark.parametrize(
    ("answers", "word"), [({"rc_image": 1}, IMAGE), ({"ss": TAKEN}, "port 8220 is taken")]
)
def test_i5_up_says_so_and_starts_nothing_without_the_image_or_the_port(
    tmp_path, share, copy, answers, word
):
    result, calls = run(tmp_path, "up", **answers)
    assert result.returncode != 0
    assert word in result.stderr
    assert not any(call.startswith("run ") for call in calls)
    assert not copy.exists()


def test_i5_the_port_probe_sees_a_socket_that_listens(tmp_path, share):
    up(tmp_path)
    asked = (tmp_path / "docker.log.ss").read_text().splitlines()
    assert any("8220" in word for word in asked)
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        # The real ss, asked as the script asks, for a port that is surely taken and then free.
        command = ["ss", *(word.replace("8220", str(taken.getsockname()[1])) for word in asked)]
        assert subprocess.run(command, capture_output=True, text=True).stdout.strip()
    assert not subprocess.run(command, capture_output=True, text=True).stdout.strip()


# ── stage.sh down ──


def test_a4_down_removes_the_container_and_the_copy_and_nothing_beside(tmp_path, share, copy):
    (share / "blattwerk-stage.txt").write_text("a note beside the copy")
    before = tree(share)
    up(tmp_path)
    assert copy.is_dir()
    result, calls = run(tmp_path, "down")
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls == [f"rm -f {NAME}"]
    assert len(result.stdout.splitlines()) == 1
    assert not copy.exists()
    # All that was there before the stage: the live folder, the backups and the note.
    assert tree(share) == before


@pytest.mark.parametrize("args", [["up", "x"], ["down", "x"], ["down", "@COPY@"], ["stop"], []])
def test_a4_stage_takes_no_path_and_no_other_word(tmp_path, share, copy, args):
    up(tmp_path)
    before = tree(share)
    result, calls = run(tmp_path, *(arg.replace("@COPY@", str(copy)) for arg in args))
    assert result.returncode == 2
    assert "usage" in result.stderr
    assert calls == []
    assert tree(share) == before


def laid_out(case, share):
    """Lays HOME out so that the copy folder is not the stage's own to remove."""
    link, where = case.split()
    copy, other = share / NAME, share.parent / "other" / NAME
    folders = {"live": share / "blattwerk", "backups": share / "blattwerk-backups", "other": other}
    if link == "copy":
        # Not even a link to a folder of the right name, far from the data.
        other.mkdir(parents=True)
        (other / "file").write_text("someone's")
        copy.symlink_to(folders[where])
        return
    # The live folder or the backups, as a link that leads to the copy, into it or above it.
    kept = folders[link]
    kept.rename(share.parent / f"real-{link}")
    (copy / "inside").mkdir(parents=True)
    (copy / "file").write_text("a copy")
    kept.symlink_to({"is": copy, "inside": copy / "inside", "holds": share}[where])


@pytest.mark.parametrize("command", ["up", "down"])
@pytest.mark.parametrize(
    "case",
    [
        "copy live",
        "copy backups",
        "copy other",
        "live is",
        "live inside",
        "live holds",
        "backups is",
        "backups inside",
        "backups holds",
    ],
)
def test_a4_stage_refuses_a_copy_folder_that_is_not_its_own(tmp_path, share, command, case):
    laid_out(case, share)
    before = tree(tmp_path / "home")
    result, calls = run(tmp_path, command)
    assert result.returncode == 1
    assert "stage: the copy folder must be" in result.stderr
    # Refused before anything else: no word to docker, and every file and link is where it was.
    assert calls == []
    assert tree(tmp_path / "home") == before


def test_i3_down_with_nothing_to_remove_succeeds(tmp_path, share, copy):
    # docker says 1 when there is no such container.
    result, calls = run(tmp_path, "down", rc_rm=1)
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls == [f"rm -f {NAME}"]
    assert not copy.exists()


# ── stage-teacher.py ──


def teacher(server, invite):
    """Runs the script as the container would: fed on stdin, the invite in the environment."""
    env = {**os.environ, "STAGE_INVITE": invite}
    with TEACHER.open() as script:
        return subprocess.run(
            [sys.executable, "-", server],
            stdin=script,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )


def test_a6_the_teacher_sees_nothing_of_another_account(server):
    other = user()
    theirs = sheet(other, [box("a", "text", TEXT)])
    kept = other.post("/api/templates", json={"name": "Meine", "doc": theirs["doc"]}).json()
    picture = upload(other)
    invite = "/einladung/" + auth.new_link(db.open_db())
    done = teacher(server, invite)
    assert done.returncode == 0, done.stderr
    first, second = done.stdout.splitlines()
    assert first == f"E-Mail: {EMAIL}"
    password = second.removeprefix("Passwort: ")
    assert invite.rsplit("/", 1)[1] not in done.stdout + done.stderr

    # The printed login, over http as the session on the stage uses it.
    login = httpx.post(f"{server}/api/login", json={"email": EMAIL, "password": password})
    assert login.status_code == 200
    assert login.json()["admin"] is False
    session = SimpleCookie(login.headers["set-cookie"])["session"].value

    def get(path):
        return httpx.get(f"{server}{path}", headers={"Cookie": f"session={session}"})

    assert get("/api/sheets").json() == []
    # The built-in templates are everyone's: their ids lie below zero.
    assert kept["id"] > 0
    assert all(template["id"] < 0 for template in get("/api/templates").json())
    assert get(f"/api/sheets/{theirs['id']}").status_code == 404
    assert get(f"/api/sheets/{theirs['id']}/pdf").status_code == 404
    assert get(f"/api/uploads/{picture}").status_code == 404
    # The admin's list is as missing as it is for every teacher.
    assert get("/api/admin/users").status_code == 404
    # And the other account still has what it had.
    assert [found["id"] for found in other.get("/api/sheets").json()] == [theirs["id"]]


def test_a5_a_dead_invite_makes_no_teacher_and_prints_no_login(server):
    done = teacher(server, "/einladung/nothing")
    assert done.returncode == 1
    assert done.stdout == ""
    assert done.stderr == "stage teacher failed: /api/signup: status 404\n"
    assert db.open_db().execute("SELECT count(*) FROM users").fetchone()[0] == 0


# ── the browser on the stage's address ──


@pytest.mark.skipif(BROWSER == "webkit", reason="WebKit keeps no Secure cookie from plain http")
def test_i1_a_browser_signs_in_on_plain_http_and_stays_signed_in(browser, server):
    email = f"{uuid4().hex}@example.com"
    user(email)
    # A new context with no cookie put in by hand: the form alone signs in, as on the stage.
    context = browser.new_context()
    try:
        page = context.new_page()
        page.goto(server)
        page.locator("#email").click()
        page.keyboard.type(email)
        page.locator("#password").click()
        page.keyboard.type(PASSWORD)
        page.keyboard.press("Enter")
        home = page.get_by_role("heading", name="Meine Blätter")
        expect(home).to_be_visible()
        (cookie,) = [c for c in context.cookies() if c["name"] == "session"]
        assert cookie["secure"]
        page.reload()
        expect(home).to_be_visible()
        expect(page.locator("#email")).to_have_count(0)
    finally:
        context.close()


# ── the docs ──


def test_i7_the_readme_names_both_tasks():
    readme = (ROOT / "README.md").read_text()
    assert "mise run stage:up" in readme
    assert "mise run stage:down" in readme
