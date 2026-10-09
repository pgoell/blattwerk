"""The deploy's smoke test: scripts/smoke.py, run as the deploy runs it, fed on stdin."""

import ast
import json
import os
import subprocess
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ui import TEXT, box, sheet, user

from blattwerk import auth, db

SCRIPT = Path(__file__).parent.parent / "scripts" / "smoke.py"
HALF = ["page", "bundle", "database"]
WHOLE = [*HALF, "signup", "login", "sheet", "editor", "save", "reload", "pdf"]
HTML = b'<html><script>let a = 1;</script><script type="module" src="/assets/app.js"></script>'


def smoke(*args, invite=None):
    env = {key: value for key, value in os.environ.items() if key != "SMOKE_INVITE"}
    if invite:
        env["SMOKE_INVITE"] = invite
    with SCRIPT.open() as script:
        return subprocess.run(
            [sys.executable, "-", *args],
            stdin=script,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )


def counts():
    con = db.open_db()
    tables = [name for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    return {name: con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0] for name in tables}


@contextmanager
def answering(bundle="text/javascript", me=401):
    """A tiny app that logs each request. Healthy as it stands; the arguments make it sick."""
    log = []

    class Handler(BaseHTTPRequestHandler):
        def answer(self):
            log.append((self.command, self.path))
            status, kind, body = {
                "/": (200, "text/html; charset=utf-8", HTML),
                "/assets/app.js": (200, bundle, b"let b = 2;"),
                "/api/me": (me, "application/json", b"{}"),
            }.get(self.path, (404, "application/json", b"{}"))
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = do_PATCH = answer

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", log
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_full_run_types_saves_reloads_and_prints_and_says_no_more_than_the_steps(server):
    token = auth.new_link(db.open_db())
    run = smoke(server, invite=f"/einladung/{token}")
    # The whole output, so no token, password, email, cookie, path or sheet text is in it.
    assert run.stderr == ""
    assert run.stdout.splitlines() == [*WHOLE, "smoke ok"]
    assert run.returncode == 0
    con = db.open_db()
    (email,) = con.execute("SELECT email FROM users").fetchone()
    assert email.startswith("smoke-") and email.endswith("@smoke.invalid")
    ((doc, version),) = con.execute("SELECT doc, version FROM sheets").fetchall()
    (block,) = json.loads(doc)["pages"][0]["blocks"]
    # The script made the block with "Probe" in it, so this word came in through the editor.
    assert block["props"]["text"].startswith("smoke") and "Probe" not in doc
    assert version > 1
    # The invite is used up.
    assert con.execute("SELECT count(*) FROM links").fetchone()[0] == 0


def test_full_run_takes_a_bare_token(server):
    run = smoke(server, invite=auth.new_link(db.open_db()))
    assert (run.returncode, run.stderr) == (0, "")


def test_full_run_with_a_used_invite_fails_and_names_no_secret(server):
    token = auth.new_link(db.open_db())
    db.open_db().execute("DELETE FROM links")
    run = smoke(server, invite=f"/einladung/{token}")
    assert run.returncode == 1
    assert run.stdout.splitlines() == HALF
    assert run.stderr == "smoke failed: signup: status 404\n"


def test_read_only_passes_and_leaves_every_row_count(server):
    sheet(user(), [box("a", "text", TEXT)])
    before = counts()
    assert before["users"] == before["sheets"] == before["sessions"] == 1
    run = smoke("--read-only", server)
    assert run.stderr == ""
    assert run.stdout.splitlines() == [*HALF, "smoke ok"]
    assert run.returncode == 0
    assert counts() == before


def test_read_only_sends_three_gets_and_nothing_else():
    with answering() as (url, log):
        run = smoke("--read-only", url)
    assert (run.returncode, run.stderr) == (0, "")
    assert log == [("GET", "/"), ("GET", "/assets/app.js"), ("GET", "/api/me")]


def test_read_only_fails_when_the_bundle_is_the_page():
    # What the app answers for a file that is not there.
    with answering(bundle="text/html; charset=utf-8") as (url, _):
        run = smoke("--read-only", url)
    assert run.returncode == 1
    assert run.stdout.splitlines() == ["page"]
    assert run.stderr == "smoke failed: bundle: content type text/html\n"


def test_read_only_fails_when_the_app_cannot_read_the_database():
    for status in (500, 503, 200):
        with answering(me=status) as (url, _):
            run = smoke("--read-only", url)
        assert run.returncode == 1
        assert run.stderr == f"smoke failed: database: status {status}\n"


def test_read_only_fails_on_a_database_that_is_no_database(server, data_dir):
    (data_dir / "blattwerk.db").write_bytes(b"not a database, not at all" * 100)
    run = smoke("--read-only", server)
    assert run.returncode == 1
    assert run.stderr.startswith("smoke failed: database: status 5")


def test_full_run_without_an_invite_fails_before_any_request():
    with answering() as (url, log):
        run = smoke(url)
    assert run.returncode == 1
    assert run.stderr == "smoke failed: invite: SMOKE_INVITE is not set\n"
    assert log == []


def test_an_app_that_is_not_there_fails_with_the_class_of_the_error_only():
    with answering() as (url, _):
        pass
    run = smoke("--read-only", url)
    assert run.returncode == 1
    assert run.stderr == "smoke failed: page: URLError\n"


def test_read_only_needs_no_playwright_and_no_pypdf():
    tree = ast.parse(SCRIPT.read_text())
    top = [node for node in tree.body if isinstance(node, ast.Import | ast.ImportFrom)]
    names = [alias.name for node in top if isinstance(node, ast.Import) for alias in node.names]
    names += [node.module or "" for node in top if isinstance(node, ast.ImportFrom)]
    assert names
    assert not [name for name in names if name.split(".")[0] in ("playwright", "pypdf")]
