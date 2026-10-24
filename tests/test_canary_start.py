"""canary.sh start copies the live data onto its own folder and refuses any other."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_canary import (
    IMAGE,
    NAME,
    ROOT,
    copy,  # noqa: F401
    live,  # noqa: F401
    refused,
    rows,
    run,
    tree,
)

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
