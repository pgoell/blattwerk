"""The daily feedback job: scripts/feedback_triage.py and feedback-cron.sh.

Every run goes through a fake gh and a fake claude on PATH, so no test reaches GitHub or the model.
"""

import fcntl
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from blattwerk import db

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "feedback_triage.py"
PIC = b"\xff\xd8fake"
STAMP = "2026-10-09T08-14-22"

# The fakes are python scripts; PYTHON is replaced by this interpreter's path.
GH = """#!PYTHON
import json, os, sys
argv = sys.argv[1:]
with open(os.environ["GH_LOG"], "a") as log:
    log.write(json.dumps(argv) + "\\n")
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

    def send(self, user, stamp, text=None, art="feedback", seite="/blatt/6", files=None):
        folder = self.data / "users" / str(user) / "feedback" / stamp
        folder.mkdir(parents=True, exist_ok=True)
        for name, content in (files or {}).items():
            (folder / name).write_bytes(content)
        fields = {"art": art, "seite": seite}
        if text is not None:
            fields["text"] = text
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

    def summary_path(self):
        return self.state / "summaries" / f"{date.today().isoformat()}.md"

    def summary(self):
        path = self.summary_path()
        return path.read_text() if path.exists() else ""


@pytest.fixture
def world(tmp_path):
    return World(tmp_path)


def test_reads_each_send_once(world):
    world.send(1, STAMP, text="bugword: undo")
    world.send(2, "2026-10-09T09-00-00", text="thanks")
    world.answer({"bugword": verdict(), "*": verdict("nothing")})
    assert world.run().returncode == 0
    assert [c[:2] for c in world.writes()] == [["issue", "create"]]
    world.clear()
    assert world.run().returncode == 0
    assert world.claude_calls() == [] and world.gh_calls() == []


def test_live_folder_is_not_written(world):
    world.send(1, "s1", text="questionword?")
    world.send(2, "s2", files={"audio-1.webm": b"voice"})
    world.send(1, "s3", art="fotos", files={"photo-1.jpg": PIC})
    world.send(2, "s4", text="bugword", files={"photo-1.heic": b"x", "screenshot-1.png": PIC})
    world.answer(
        {"questionword": verdict("question"), "bugword": verdict(), "*": verdict("nothing")}
    )
    chmod_tree(world.data, 0o555, 0o444)
    try:
        before = tree(world.data)
        result = world.run()
        after = tree(world.data)
    finally:
        chmod_tree(world.data, 0o755, 0o644)
    assert result.returncode == 0, result.stderr
    assert after == before


@pytest.mark.parametrize("where", ["same", "inside", "holds"])
def test_refuses_state_inside_data(world, where):
    world.send(1, STAMP, text="bugword")
    data = world.data
    state = {"same": data, "inside": data / "state", "holds": world.root}[where]
    before = tree(data)
    result = world.run(state=state)
    assert result.returncode == 2
    assert world.gh_calls() == [] and world.claude_calls() == []
    assert tree(data) == before


@pytest.mark.parametrize("kind", ["question", "nothing"])
def test_question_and_nothing_open_no_issue(world, kind):
    world.send(1, STAMP, text="questionword")
    world.answer({"*": verdict(kind)})
    assert world.run().returncode == 0
    assert world.writes() == []
    assert world.read()[f"1/{STAMP}"]["outcome"] == kind


def test_match_comments_on_open_issue(world):
    world.send(1, STAMP, text="bugword")
    world.answer({"*": verdict(issue=12)})
    result = world.run(GH_ISSUES=json.dumps([{"number": 12, "title": "Undo"}]))
    assert result.returncode == 0, result.stderr
    assert [c[:3] for c in world.writes()] == [["issue", "comment", "12"]]


def test_match_unknown_number_opens_issue(world):
    world.send(1, STAMP, text="bugword")
    world.answer({"*": verdict(issue=999)})
    result = world.run(GH_ISSUES=json.dumps([{"number": 12, "title": "Undo"}]))
    assert result.returncode == 0, result.stderr
    assert [c[:2] for c in world.writes()] == [["issue", "create"]]


@pytest.mark.parametrize("kind", ["bug", "wish"])
def test_new_issue_labels(world, kind):
    world.send(1, STAMP, text="bugword")
    world.answer({"*": verdict(kind, title="Undo loses page", body="Steps here.")})
    assert world.run().returncode == 0
    (create,) = world.writes()
    assert create[:2] == ["issue", "create"]
    assert value(create, "--repo") == "pgoell/blattwerk"
    assert value(create, "--title") == "Undo loses page"
    body = value(create, "--body")
    assert "Steps here." in body and "restated by the daily feedback job" in body
    labels = [create[i + 1] for i, arg in enumerate(create) if arg == "--label"]
    assert labels == ["feedback", kind]


def test_private_hit_is_not_filed(world):
    world.send(1, STAMP, text="bugword")
    world.answer({"*": verdict(body="Ask anna.schmidt@example.org about it.")})
    assert world.run().returncode == 0
    assert world.writes() == []
    assert world.read()[f"1/{STAMP}"]["outcome"] == "refused"
    assert f"1/{STAMP}" in section(world.summary(), "Left for Pascal")


def test_no_file_reaches_gh(world):
    files = {"photo-1.jpg": PIC, "screenshot-1.png": PIC, "audio-1.webm": b"voice"}
    world.send(1, STAMP, text="bugword", files=files)
    world.answer({"*": verdict()})
    assert world.run().returncode == 0
    assert world.gh_calls()
    names = [STAMP, "feedback.json", *files]
    for argv in world.gh_calls():
        assert argv[:2] in (["issue", "list"], ["issue", "create"], ["issue", "comment"])
        assert "--body-file" not in argv and "-F" not in argv
        for arg in argv:
            assert str(world.data) not in arg
            assert not any(name in arg for name in names)


def test_voice_only_is_to_hear(world):
    world.send(1, STAMP, text="", files={"audio-1.webm": b"voice"})
    assert world.run().returncode == 0
    assert world.claude_calls() == [] and world.writes() == []
    assert world.read()[f"1/{STAMP}"]["outcome"] == "to hear"
    assert "audio-1.webm" in section(world.summary(), "To hear")


def test_voice_with_text_is_triaged(world):
    world.send(1, STAMP, text="bugword", files={"audio-1.webm": b"voice"})
    world.answer({"*": verdict()})
    assert world.run().returncode == 0
    (call,) = world.claude_calls()
    assert "cannot hear: 1" in call["stdin"]
    assert [c[:2] for c in world.writes()] == [["issue", "create"]]
    assert "audio-1.webm" in section(world.summary(), "To hear")


def test_summary_names_what_happened(world):
    world.send(1, "2026-10-09T08-00-00", text="bugword")
    world.send(1, "2026-10-09T09-00-00", text="commentword")
    world.send(1, "2026-10-09T10-00-00", text="questionword")
    world.send(2, "2026-10-09T08-00-00", text="failword")
    world.answer(
        {
            "bugword": verdict(title="Good undo"),
            "commentword": verdict(issue=12),
            "questionword": verdict("question"),
            "failword": "FAIL",
            "*": verdict("nothing"),
        }
    )
    open_issues = json.dumps([{"number": 12, "title": "Undo loses page"}])
    result = world.run(GH_ISSUES=open_issues)
    assert result.returncode == 1
    summary = world.summary()
    assert "Sends read: 3" in summary
    assert "[bug]" in section(summary, "Opened") and "1/2026-10-09T08-00-00" in section(
        summary, "Opened"
    )
    assert "#12" in section(summary, "Commented")
    assert "1/2026-10-09T10-00-00" in section(summary, "Left for Pascal")
    assert "2/2026-10-09T08-00-00" in section(summary, "Failed, tried again next run")


def test_no_summary_without_new_send(world):
    assert world.run().returncode == 0
    assert not (world.state / "summaries").exists()
    world.send(1, STAMP, text="questionword")
    world.answer({"*": verdict("question")})
    assert world.run().returncode == 0
    before = world.summary_path().read_bytes()
    world.clear()
    assert world.run().returncode == 0
    assert world.summary_path().read_bytes() == before
    assert world.claude_calls() == [] and world.gh_calls() == []


def test_fotos_send_always_on_summary(world):
    world.send(1, STAMP, art="fotos", text=None, files={"photo-1.jpg": PIC})
    world.answer({"*": verdict("nothing")})
    assert world.run().returncode == 0
    assert world.read()[f"1/{STAMP}"]["outcome"] == "nothing"
    left = section(world.summary(), "Left for Pascal")
    assert f"- photos of a sheet to look at (1/{STAMP})" in left


@pytest.mark.parametrize("mode_", ["model-fails", "model-garbage", "gh-create-fails"])
def test_failed_send_retried(world, mode_):
    world.send(1, "s1", text="bugword")
    world.send(2, "s2", text="failword")
    fails = {"model-fails": "FAIL", "model-garbage": "GARBAGE"}
    failing = fails.get(mode_, verdict(title="Broken undo"))
    world.answer(
        {"bugword": verdict(title="Good undo"), "failword": failing, "*": verdict("nothing")}
    )
    extra = {"GH_RC_CREATE": "1", "GH_FAIL_ON": "Broken"} if mode_ == "gh-create-fails" else {}
    result = world.run(**extra)
    assert result.returncode == 1
    assert "1/s1" in world.read() and "2/s2" not in world.read()
    assert any(value(c, "--title") == "Good undo" for c in world.writes())
    world.answer({"bugword": verdict(), "failword": verdict(title="Broken undo"), "*": verdict()})
    world.clear()
    assert world.run().returncode == 0
    assert world.read()["2/s2"]["outcome"] == "filed"


def test_dry_run_writes_nothing(world):
    world.send(1, STAMP, text="bugword")
    world.answer({"*": verdict(title="Undo loses page", body="Steps here.")})
    result = world.run("--dry-run")
    assert result.returncode == 0, result.stderr
    assert "would file [bug]" in result.stdout
    assert "Undo loses page" in result.stdout and "Steps here." in result.stdout
    assert all(c[:2] == ["issue", "list"] for c in world.gh_calls())
    assert not world.state.exists()


@pytest.mark.parametrize("damage", ["missing", "not-a-database"])
def test_unreadable_users_table_files_nothing(world, damage):
    world.send(1, STAMP, text="bugword")
    db_path = world.data / "blattwerk.db"
    if damage == "missing":
        db_path.unlink()
    else:
        db_path.write_bytes(b"this is not a database" * 100)
    world.answer({"*": verdict()})
    result = world.run()
    assert result.returncode == 1
    assert "cannot read the users table" in result.stderr
    assert world.writes() == []
    assert not (world.state / "read.json").exists()


BAD_VERDICTS = [
    pytest.param({"verdict": "praise", "title": "x", "body": "x", "issue": None}, id="kind"),
    pytest.param(verdict(title=" "), id="empty-title"),
    pytest.param(verdict(title="x" * 121), id="long-title"),
    pytest.param(verdict(body="x" * 4001), id="long-body"),
    pytest.param(verdict(issue="12"), id="issue-string"),
    pytest.param(verdict(issue=True), id="issue-bool"),
    pytest.param(["bug", "a"], id="list"),
]


@pytest.mark.parametrize("answer", BAD_VERDICTS)
def test_bad_verdict_fails_send(world, answer):
    world.send(1, STAMP, text="bugword")
    world.answer({"*": answer})
    assert world.run().returncode == 1
    assert world.writes() == []
    assert f"1/{STAMP}" not in world.read()


def test_model_gets_no_tools(world):
    files = {"photo-1.jpg": PIC, "screenshot-1.png": PIC, "photo-2.heic": b"x"}
    world.send(1, STAMP, text="bugword", files=files)
    world.answer({"*": verdict()})
    world.run()
    (call,) = world.claude_calls()
    argv = call["argv"]
    assert argv[argv.index("--tools") + 1] == ""
    assert argv[argv.index("--setting-sources") + 1] == ""
    assert "--strict-mcp-config" in argv and "--no-session-persistence" in argv
    assert not any(str(world.data) in arg for arg in argv)
    assert str(world.data) not in call["stdin"]
    content = json.loads(call["stdin"])["message"]["content"]
    assert sum(block["type"] == "image" for block in content) == 2


def test_model_with_tools_stops_run(world):
    world.send(1, "s1", text="toolword")
    world.send(2, "s2", text="bugword")
    world.answer({"toolword": "TOOLS", "*": verdict()})
    result = world.run()
    assert result.returncode == 1
    assert "the model has tools, stopping" in result.stderr
    assert len(world.claude_calls()) == 1
    assert world.writes() == [] and world.read() == {}


def test_model_without_init_fails_send(world):
    world.send(1, "s1", text="noinitword")
    world.send(2, "s2", text="bugword")
    world.answer({"noinitword": "NOINIT", "bugword": verdict(), "*": verdict("nothing")})
    assert world.run().returncode == 1
    assert "1/s1" not in world.read()
    assert [c[:2] for c in world.writes()] == [["issue", "create"]]
    assert world.read()["2/s2"]["outcome"] == "filed"


def test_odd_gh_answer_still_marks_read(world):
    world.send(1, STAMP, text="bugword")
    world.answer({"*": verdict()})
    result = world.run(GH_CREATE_OUT="created")
    assert result.returncode == 0, result.stderr
    assert world.read()[f"1/{STAMP}"] == {"outcome": "filed", "issue": None}
    world.clear()
    assert world.run(GH_CREATE_OUT="created").returncode == 0
    assert world.writes() == []


def test_half_written_send_skipped(world):
    folder = world.data / "users" / "1" / "feedback" / "s1"
    folder.mkdir(parents=True)
    (folder / "screenshot-1.png").write_bytes(PIC)
    assert world.run().returncode == 0
    assert world.claude_calls() == [] and "1/s1" not in world.read()
    (folder / "feedback.json").write_text(json.dumps({"art": "feedback", "text": "bugword"}))
    world.answer({"*": verdict()})
    assert world.run().returncode == 0
    assert len(world.claude_calls()) == 1
    assert world.read()["1/s1"]["outcome"] == "filed"


def test_second_run_leaves(world):
    world.send(1, STAMP, text="bugword")
    world.state.mkdir()
    fd = os.open(world.state / "lock", os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        result = world.run()
    finally:
        os.close(fd)
    assert result.returncode == 0
    assert "another run holds the lock" in result.stdout
    assert world.claude_calls() == [] and world.gh_calls() == []


@pytest.mark.parametrize("text", ["bugword", None])
@pytest.mark.parametrize(
    "name, content",
    [("photo-1.heic", b"heic"), ("photo-1.jpg", b"x" * 3_500_001)],
    ids=["heic", "too-big"],
)
def test_unusable_picture_is_to_see(world, name, content, text):
    world.send(1, STAMP, text=text, files={name: content})
    world.answer({"*": verdict()})
    result = world.run()
    key = f"1/{STAMP}"
    if text is None:
        assert world.claude_calls() == [] and world.writes() == []
        assert world.read()[key]["outcome"] == "to see"
        return
    assert result.returncode == 0, result.stderr
    (call,) = world.claude_calls()
    blocks = json.loads(call["stdin"])["message"]["content"]
    assert not any(block["type"] == "image" for block in blocks)
    assert key in section(world.summary(), "Left for Pascal")


def test_state_modes(world):
    world.send(1, STAMP, text="questionword")
    world.answer({"*": verdict("question")})
    assert world.run().returncode == 0
    assert mode(world.state) == 0o700
    assert mode(world.state / "read.json") == 0o600
    assert mode(world.state / "summaries") == 0o700
    assert mode(world.summary_path()) == 0o600


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_cron_runs_the_code_of_origin_master(world, tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git is missing")
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    for name in ("feedback_triage.py", "feedback_privacy.py", "feedback-cron.sh"):
        shutil.copy2(ROOT / "scripts" / name, repo / "scripts" / name)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "test")
    _git(repo, "config", "user.email", "test@example.org")
    _git(repo, "add", "scripts")
    _git(repo, "-c", "commit.gpgsign=false", "commit", "-qm", "copy")
    _git(repo, "update-ref", "refs/remotes/origin/master", "HEAD")
    # The working copy is not what origin/master holds: the cron job must run the committed one.
    (repo / "scripts" / "feedback_triage.py").write_text("raise SystemExit(9)\n")
    world.send(1, STAMP, text="bugword")
    world.answer({"*": verdict()})
    result = subprocess.run(
        [
            str(repo / "scripts" / "feedback-cron.sh"),
            "--data",
            str(world.data),
            "--state",
            str(world.state),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        env=world.env(),
    )
    assert result.returncode == 0, result.stderr
    assert [c[:2] for c in world.writes()] == [["issue", "create"]]
