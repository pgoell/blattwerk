"""The daily feedback job: scripts/feedback_triage.py and feedback-cron.sh.

Every run goes through a fake gh and a fake claude on PATH, so no test reaches GitHub or the model.
"""

# Tests of one behaviour each live in the sibling modules. Shared helpers stay here so existing imports keep working.

import ast
import hashlib
import json
import os
import sqlite3
import stat
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import pytest

from blattwerk import db

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "feedback_triage.py"
PIC = b"\xff\xd8fake"
STAMP = "2026-10-09T08-14-22"
# The model prompt of scripts/feedback_triage.py as it stood before the line-length rule came off.
SYSTEM_SHA256 = "6722fc32a2fcdcb56710c8494049a25fdbc1e3c2278ec64d8906b8377fc0d10d"

# The fakes are python scripts; PYTHON is replaced by this interpreter's path.
GH = """#!PYTHON
import json, os, sys, time
argv = sys.argv[1:]
with open(os.environ["GH_LOG"], "a") as log:
    log.write(json.dumps(argv) + "\\n")
# GH_HANG_ON: a word in an argument. The call is logged, then gh does not answer for 5 s.
if os.environ.get("GH_HANG_ON") and os.environ["GH_HANG_ON"] in " ".join(argv):
    time.sleep(5)
if argv[:2] == ["issue", "list"]:
    print(os.environ.get("GH_ISSUES", "[]"))
    sys.exit(int(os.environ.get("GH_RC_LIST", "0")))
title = argv[argv.index("--title") + 1] if "--title" in argv else ""
if int(os.environ.get("GH_RC_CREATE", "0")) and os.environ.get("GH_FAIL_ON", "") in title:
    sys.exit(1)
if argv[:2] == ["issue", "create"]:
    print(os.environ.get("GH_CREATE_OUT", "https://github.com/pgoell/blattwerk/issues/501"))
"""

# Answers by marker: the first key found in the stdin, else "*". The init line says what the model
# can reach. "FAIL" exits with no result, "GARBAGE" answers text that is not JSON.
CLAUDE = """#!PYTHON
import json, os, sys
stdin = sys.stdin.read()
with open(os.environ["CLAUDE_LOG"], "a") as log:
    log.write(json.dumps({"argv": sys.argv[1:], "stdin": stdin}) + "\\n")
answers = json.load(open(os.environ["CLAUDE_ANSWERS"]))
key = next((k for k in answers if k != "*" and k in stdin), "*")
answer = answers[key]
init = {"type": "system", "subtype": "init", "tools": [], "mcp_servers": []}
if answer == "TOOLS":
    init["tools"] = ["Bash"]
if answer != "NOINIT":
    print(json.dumps(init))
if answer == "FAIL":
    sys.exit(1)
if answer == "NOINIT":
    answer = {"verdict": "bug", "title": "Undo", "body": "Click undo.", "issue": None}
text = "not json" if answer == "GARBAGE" else json.dumps(answer)
print(json.dumps({"type": "result", "is_error": False, "result": text}))
"""


def verdict(kind="bug", title="Undo loses the page", issue=None, body="Click undo twice."):
    return {"verdict": kind, "title": title, "body": body, "issue": issue}


def value(argv, flag):
    return argv[argv.index(flag) + 1]


def section(summary, head):
    """The text under one `## head` of a summary, '' when that section is not there."""
    parts = summary.split(f"## {head}\n")
    return parts[1].split("\n## ")[0] if len(parts) > 1 else ""


def constant(name):
    """The value of a module-level assignment in the script, read from its source."""
    body = ast.parse(SCRIPT.read_text(encoding="utf-8")).body
    assigns = [n for n in body if isinstance(n, ast.Assign)]
    (node,) = [n for n in assigns if isinstance(n.targets[0], ast.Name) and n.targets[0].id == name]
    return ast.literal_eval(node.value)


def make_old(folder):
    """Sets the folder's time of change two hours back."""
    old = time.time() - 7200
    os.utime(folder, (old, old))


def tree(folder):
    """Every path under `folder` with its mode, size, hash and time of change."""
    found = {}
    for path in sorted(folder.rglob("*")):
        stat_ = path.lstat()
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        found[str(path.relative_to(folder))] = (
            stat_.st_mode,
            stat_.st_size,
            digest,
            stat_.st_mtime_ns,
        )
    return found


def chmod_tree(folder, dir_mode, file_mode):
    for path in list(folder.rglob("*")):
        path.chmod(dir_mode if path.is_dir() else file_mode)
    folder.chmod(dir_mode)


def mode(path):
    return stat.S_IMODE(path.stat().st_mode)


class World:
    """A made-up data folder with two users, the fakes on PATH, and the logs they write."""

    def __init__(self, root: Path):
        self.root = root
        self.data = root / "live"
        self.state = root / "state"
        self.bin = root / "bin"
        self.gh_log = root / "gh.log"
        self.claude_log = root / "claude.log"
        self.answers_file = root / "answers.json"
        self.bin.mkdir()
        (root / "home").mkdir()
        self.data.mkdir()
        for name, text in (("gh", GH), ("claude", CLAUDE)):
            (self.bin / name).write_text(text.replace("PYTHON", sys.executable))
            (self.bin / name).chmod(0o755)
        con = sqlite3.connect(self.data / "blattwerk.db")
        con.executescript(db.SCHEMA)
        for email in ("anna.schmidt@example.org", "ben@example.org"):
            con.execute("INSERT INTO users (email, password) VALUES (?, 'x')", (email,))
        con.commit()
        con.close()
        self.answer({"*": verdict("nothing")})

    def send(
        self, user, stamp, text=None, art="feedback", seite="/blatt/6", files=None, extra=None
    ):
        folder = self.data / "users" / str(user) / "feedback" / stamp
        folder.mkdir(parents=True, exist_ok=True)
        for name, content in (files or {}).items():
            (folder / name).write_bytes(content)
        fields = {"art": art}
        if seite is not None:
            fields["seite"] = seite
        if text is not None:
            fields["text"] = text
        fields.update(extra or {})
        (folder / "feedback.json").write_text(json.dumps(fields))
        return folder

    def answer(self, answers):
        self.answers_file.write_text(json.dumps(answers))

    def env(self, **extra):
        path = f"{self.bin}{os.pathsep}{os.environ['PATH']}"
        return {
            **os.environ,
            "HOME": str(self.root / "home"),
            "PATH": path,
            "GH_LOG": str(self.gh_log),
            "CLAUDE_LOG": str(self.claude_log),
            "CLAUDE_ANSWERS": str(self.answers_file),
            **extra,
        }

    def run(self, *args, state=None, **extra):
        command = [sys.executable, str(SCRIPT), "--data", str(self.data)]
        command += ["--state", str(state or self.state), *args]
        return subprocess.run(
            command, capture_output=True, text=True, timeout=60, env=self.env(**extra)
        )

    def clear(self):
        self.gh_log.unlink(missing_ok=True)
        self.claude_log.unlink(missing_ok=True)

    def gh_calls(self):
        if not self.gh_log.exists():
            return []
        return [json.loads(line) for line in self.gh_log.read_text().splitlines()]

    def writes(self):
        return [c for c in self.gh_calls() if c[:2] in (["issue", "create"], ["issue", "comment"])]

    def claude_calls(self):
        if not self.claude_log.exists():
            return []
        return [json.loads(line) for line in self.claude_log.read_text().splitlines()]

    def read(self):
        path = self.state / "read.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def pending(self):
        path = self.state / "pending.json"
        return json.loads(path.read_text()) if path.exists() else {"tries": {}, "half": []}

    def summary_path(self):
        return self.state / "summaries" / f"{date.today().isoformat()}.md"

    def summary(self):
        path = self.summary_path()
        return path.read_text() if path.exists() else ""


@pytest.fixture
def world(tmp_path):
    return World(tmp_path)


BAD_VERDICTS = [
    pytest.param({"verdict": "praise", "title": "x", "body": "x", "issue": None}, id="kind"),
    pytest.param(verdict(title=" "), id="empty-title"),
    pytest.param(verdict(title="x" * 121), id="long-title"),
    pytest.param(verdict(body="x" * 4001), id="long-body"),
    pytest.param(verdict(issue="12"), id="issue-string"),
    pytest.param(verdict(issue=True), id="issue-bool"),
    pytest.param(["bug", "a"], id="list"),
]


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
