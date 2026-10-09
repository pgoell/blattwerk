"""The deploy's way back: snapshot.py, keep-prev.sh and their place in deploy.yml."""

import os
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from blattwerk import db

ROOT = Path(__file__).parent.parent
SHA = "abc123"


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "live" / "blattwerk.db"
    path.parent.mkdir()
    con = sqlite3.connect(path)
    con.executescript(db.SCHEMA)
    for n in range(3):
        add_user(con, f"u{n}@example.org")
    con.execute("INSERT INTO sheets (user_id, title, doc) VALUES (1, 'Blatt', '{}')")
    con.commit()
    con.close()
    return path


@pytest.fixture
def target(tmp_path):
    return tmp_path / "backups"


def add_user(con, email):
    con.execute("INSERT INTO users (email, password) VALUES (?, 'x')", (email,))


def snapshot(source, target, *args):
    script = [sys.executable, str(ROOT / "scripts" / "snapshot.py")]
    command = [*script, str(source), str(target), SHA, *args]
    return subprocess.run(command, capture_output=True, text=True, timeout=20)


def users(path):
    con = sqlite3.connect(path)
    try:
        return con.execute("SELECT count(*) FROM users").fetchone()[0]
    finally:
        con.close()


def names(folder):
    return sorted(p.name for p in folder.iterdir()) if folder.exists() else []


def test_snapshot_copies_the_database(source, target):
    before = source.read_bytes()
    result = snapshot(source, target)
    assert result.returncode == 0, result.stderr
    assert names(target) == [f"pre-{SHA}.db"]
    live, copy = sqlite3.connect(source), sqlite3.connect(target / f"pre-{SHA}.db")
    tables = [name for (name,) in live.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    assert {"users", "sheets", "links"} <= set(tables)
    for name in tables:
        count = f"SELECT count(*) FROM {name}"
        assert copy.execute(count).fetchone() == live.execute(count).fetchone()
    assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    live.close()
    copy.close()
    assert source.read_bytes() == before
    assert "users=3" in result.stdout


def test_snapshot_opens_the_source_read_only(source, target):
    source.chmod(0o444)
    source.parent.chmod(0o555)
    try:
        result = snapshot(source, target)
    finally:
        source.parent.chmod(0o755)
        source.chmod(0o644)
    assert result.returncode == 0, result.stderr
    assert users(target / f"pre-{SHA}.db") == 3


def test_snapshot_waits_for_a_writer(source, target):
    writer = sqlite3.connect(source, isolation_level=None, check_same_thread=False)
    writer.execute("BEGIN EXCLUSIVE")
    add_user(writer, "late@example.org")

    def commit():
        time.sleep(0.5)
        writer.execute("COMMIT")

    thread = threading.Thread(target=commit)
    thread.start()
    try:
        result = snapshot(source, target)
    finally:
        thread.join()
        writer.close()
    assert result.returncode == 0, result.stderr
    assert users(target / f"pre-{SHA}.db") == 4


def test_failed_snapshot_leaves_no_file(source, target, tmp_path):
    writer = sqlite3.connect(source, isolation_level=None)
    writer.execute("BEGIN EXCLUSIVE")
    try:
        result = snapshot(source, target, "--timeout", "0.2")
    finally:
        writer.close()
    assert result.returncode != 0
    assert "locked" in result.stderr
    assert names(target) == []

    garbage = tmp_path / "garbage.db"
    garbage.write_bytes(b"not a database, not at all" * 100)
    result = snapshot(garbage, target)
    assert result.returncode != 0
    assert result.stderr
    assert names(target) == []


def test_prune_keeps_the_newest_30(source, target):
    target.mkdir()
    for n in range(35):
        old = target / f"pre-old{n:02}.db"
        old.write_bytes(b"")
        # The higher the number, the newer the file; all of them older than the new one.
        os.utime(old, (1_700_000_000 + n, 1_700_000_000 + n))
    result = snapshot(source, target)
    assert result.returncode == 0, result.stderr
    assert names(target) == sorted([f"pre-{SHA}.db", *(f"pre-old{n:02}.db" for n in range(6, 35))])
    assert "pre-old05.db" in result.stdout


def test_prune_spares_the_new_snapshot(source, target):
    target.mkdir()
    ahead = time.time() + 86400
    for n in range(30):
        (target / f"pre-ahead{n}.db").write_bytes(b"")
        os.utime(target / f"pre-ahead{n}.db", (ahead + n, ahead + n))
    assert snapshot(source, target).returncode == 0
    assert f"pre-{SHA}.db" in names(target)
    assert len(names(target)) == 30


def test_snapshot_leaves_a_hot_journal_alone(source, target):
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
    subprocess.run([sys.executable, "-c", crash, str(source)], check=True)
    journal = source.with_name("blattwerk.db-journal")
    held = journal.read_bytes()
    assert held
    result = snapshot(source, target)
    assert result.returncode != 0
    assert "Open the site once" in result.stderr
    assert journal.read_bytes() == held
    assert names(target) == []


def test_prune_spares_other_files(source, target):
    target.mkdir()
    (target / "blattwerk-2026-10-09-pr184.db").write_bytes(b"by hand")
    (target / "notes.txt").write_text("keep")
    (target / "pre-folder.db").mkdir()
    (target / "sub").mkdir()
    (target / "pre-old.db").write_bytes(b"")
    os.utime(target / "pre-old.db", (1_700_000_000, 1_700_000_000))
    result = snapshot(source, target, "--keep", "1")
    assert result.returncode == 0, result.stderr
    kept = ["blattwerk-2026-10-09-pr184.db", "notes.txt", f"pre-{SHA}.db", "pre-folder.db", "sub"]
    assert names(target) == sorted(kept)


def test_no_database_skips(tmp_path, target):
    result = snapshot(tmp_path / "live" / "blattwerk.db", target)
    assert result.returncode == 0
    assert "nothing to snapshot" in result.stdout
    assert names(target) == []
    assert not (tmp_path / "live").exists()


def test_rerun_keeps_the_first_snapshot(source, target):
    assert snapshot(source, target).returncode == 0
    con = sqlite3.connect(source)
    add_user(con, "later@example.org")
    con.commit()
    con.close()
    assert snapshot(source, target).returncode == 0
    assert snapshot(source, target).returncode == 0
    assert names(target) == [f"pre-{SHA}-2.db", f"pre-{SHA}-3.db", f"pre-{SHA}.db"]
    assert users(target / f"pre-{SHA}.db") == 3
    assert users(target / f"pre-{SHA}-2.db") == 4


def test_snapshot_mode_600(source, target):
    assert snapshot(source, target).returncode == 0
    assert (target / f"pre-{SHA}.db").stat().st_mode & 0o777 == 0o600


DOCKER = """#!/usr/bin/env bash
echo "$*" >> "$DOCKER_LOG"
case "$1" in
  inspect) [ "$INSPECT_RC" = 0 ] && echo sha256:abc; exit "$INSPECT_RC" ;;
  exec) exit "$EXEC_RC" ;;
esac
"""


def keep_prev(tmp_path, inspect=0, exec_=0):
    """Runs keep-prev.sh against a docker that only writes down what it was asked."""
    stub = tmp_path / "bin" / "docker"
    stub.parent.mkdir()
    stub.write_text(DOCKER)
    stub.chmod(0o755)
    log = tmp_path / "docker.log"
    env = {
        **os.environ,
        "PATH": f"{stub.parent}:{os.environ['PATH']}",
        "DOCKER_LOG": str(log),
        "INSPECT_RC": str(inspect),
        "EXEC_RC": str(exec_),
    }
    command = ["bash", str(ROOT / "scripts" / "keep-prev.sh")]
    result = subprocess.run(command, capture_output=True, text=True, timeout=20, env=env)
    return result, log.read_text().splitlines()


def test_keep_prev_tags_the_running_image(tmp_path):
    result, calls = keep_prev(tmp_path)
    assert result.returncode == 0, result.stderr
    assert calls[0] == "inspect -f {{.Image}} blattwerk"
    assert calls[1].startswith("exec blattwerk /app/.venv/bin/python -c ")
    assert calls[2:] == ["tag sha256:abc blattwerk-blattwerk:prev"]


def test_keep_prev_skips_without_container(tmp_path):
    result, calls = keep_prev(tmp_path, inspect=1)
    assert result.returncode == 0, result.stderr
    assert "nothing to keep" in result.stdout
    assert len(calls) == 1


def test_keep_prev_spares_prev_when_the_app_is_down(tmp_path):
    result, calls = keep_prev(tmp_path, exec_=1)
    assert result.returncode == 0, result.stderr
    assert "::warning::" in result.stdout
    assert not any(call.startswith("tag") for call in calls)


def test_deploy_snapshots_before_the_build():
    text = (ROOT / ".github" / "workflows" / "deploy.yml").read_text()
    steps = [
        "actions/checkout",
        "scripts/snapshot.py",
        "scripts/keep-prev.sh",
        "docker compose build",
    ]
    at = [text.index(step) for step in steps]
    assert at == sorted(at)
    assert "continue-on-error" not in text
