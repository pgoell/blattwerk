"""Pending state, a half-written send and the cron job that runs origin/master."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import fcntl
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess

import pytest
from test_feedback_triage import (
    PIC,
    ROOT,
    SCRIPT,
    STAMP,
    SYSTEM_SHA256,
    _git,
    constant,
    make_old,
    mode,
    section,
    value,
    verdict,
    world,  # noqa: F401
)


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


@pytest.mark.parametrize("issue", [None, 12], ids=["create", "comment"])
def test_gh_write_that_times_out_is_not_sent_again(world, issue):
    world.send(1, STAMP, text="bugword")
    world.answer({"*": verdict(issue=issue, title="Undo loses page", body="hangword here.")})
    open_issues = json.dumps([{"number": 12, "title": "Undo"}])
    extra = {"GH_HANG_ON": "hangword", "FEEDBACK_GH_TIMEOUT": "1", "GH_ISSUES": open_issues}
    result = world.run(**extra)
    assert result.returncode == 0, result.stderr
    key = f"1/{STAMP}"
    assert world.read()[key]["outcome"] == "maybe filed"
    head = section(world.summary(), "May be filed, look on GitHub")
    assert key in head and "gh did not answer in time" in head and "Undo loses page" in head
    expected = ["issue", "comment"] if issue else ["issue", "create"]
    assert [c[:2] for c in world.writes()] == [expected]
    world.clear()
    assert world.run(GH_ISSUES=open_issues).returncode == 0
    assert world.writes() == [] and world.claude_calls() == []


def test_send_that_fails_for_ever_ends_after_five_tries(world):
    world.send(1, STAMP, text="failword")
    world.answer({"*": "FAIL"})
    key = f"1/{STAMP}"
    for attempt in range(1, 5):
        world.summary_path().unlink(missing_ok=True)
        assert world.run().returncode == 1
        assert key not in world.read()
        failed = section(world.summary(), "Failed, tried again next run")
        assert f"(try {attempt} of 5)" in failed
        assert world.pending()["tries"] == {key: attempt}
    world.summary_path().unlink()
    assert world.run().returncode == 1
    assert world.read()[key] == {"outcome": "gave up", "issue": None}
    gave_up = section(world.summary(), "Gave up after 5 tries, left for Pascal")
    assert key in gave_up and "the model call failed" in gave_up
    assert key not in world.pending()["tries"]
    before = world.summary()
    world.clear()
    assert world.run().returncode == 0
    assert world.claude_calls() == [] and world.summary() == before


def test_send_that_settles_after_a_failure_drops_its_count(world):
    world.send(1, STAMP, text="bugword")
    key = f"1/{STAMP}"
    world.answer({"*": "FAIL"})
    assert world.run().returncode == 1
    assert world.pending()["tries"] == {key: 1}
    world.answer({"*": verdict()})
    assert world.run().returncode == 0
    assert key not in world.pending()["tries"]
    assert world.read()[key]["outcome"] == "filed"


def test_half_written_send_is_named_once_and_read_when_whole(world):
    folder = world.data / "users" / "1" / "feedback" / "s1"
    folder.mkdir(parents=True)
    (folder / "screenshot-1.png").write_bytes(PIC)
    make_old(folder)
    result = world.run()
    assert result.returncode == 0, result.stderr
    assert world.claude_calls() == [] and world.gh_calls() == []
    head = section(world.summary(), "Cut off halfway, no feedback.json")
    assert "1/s1" in head and "screenshot-1.png" in head
    assert "1/s1" not in world.read()
    before = world.summary()
    assert world.run().returncode == 0
    assert world.summary() == before
    (folder / "feedback.json").write_text(json.dumps({"art": "feedback", "text": "bugword"}))
    world.answer({"*": verdict()})
    assert world.run().returncode == 0
    assert world.read()["1/s1"]["outcome"] == "filed"


def test_dry_run_counts_no_try_and_names_a_half_written_send(world):
    world.send(1, STAMP, text="failword")
    folder = world.data / "users" / "2" / "feedback" / "s2"
    folder.mkdir(parents=True)
    (folder / "photo-1.jpg").write_bytes(PIC)
    make_old(folder)
    world.answer({"*": "FAIL"})
    result = world.run("--dry-run")
    assert result.returncode == 1
    assert "== 2/s2: half-written" in result.stdout
    assert f"== 1/{STAMP}: failed" in result.stdout
    assert not world.state.exists()


def test_read_json_never_holds_an_unsettled_send(world):
    world.send(1, "s1", text="failword")
    folder = world.data / "users" / "2" / "feedback" / "s2"
    folder.mkdir(parents=True)
    (folder / "photo-1.jpg").write_bytes(PIC)
    make_old(folder)
    world.answer({"failword": "FAIL", "*": verdict()})
    assert world.run().returncode == 1
    read = world.read()
    assert "1/s1" not in read and "2/s2" not in read
    assert all(v["outcome"] not in ("failed", "half-written") for v in read.values())
    master = {"1/s1": {"outcome": "filed", "issue": 7}}
    (world.state / "read.json").write_text(json.dumps(master))
    world.clear()
    assert world.run().returncode == 0
    assert world.claude_calls() == [] and world.writes() == []


def test_only_the_prompt_is_free_of_the_line_length_rule():
    source = SCRIPT.read_text(encoding="utf-8")
    assert not any(line.strip().startswith("# ruff: noqa") for line in source.splitlines())
    prompt = constant("SYSTEM")
    assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == SYSTEM_SHA256


def test_nothing_new_reaches_github(world):
    world.send(1, STAMP, text="bugword")
    world.answer({"*": verdict(title="Undo loses page", body="Click undo twice.")})
    assert world.run().returncode == 0
    (create,) = world.writes()
    flags = [arg for arg in create if arg.startswith("--")]
    assert flags == ["--repo", "--title", "--body", "--label", "--label"]
    assert value(create, "--body") == "Click undo twice.\n\n" + constant("FOOTER")


def test_a_folder_gone_meanwhile_is_no_cut_off_send(tmp_path, monkeypatch):
    """Review: an account deleted between the listing and the look at its folder's age."""
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("feedback_triage_under_test", SCRIPT)
    assert spec and spec.loader
    triage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(triage)
    monkeypatch.setattr(triage, "send_folders", lambda data: [("1/gone", tmp_path / "gone")])
    assert triage.find_half(tmp_path, {}, {"tries": {}, "half": []}) == []


@pytest.mark.parametrize("broken", ["{", "[]", '{"tries": 3}'])
def test_a_broken_pending_file_does_not_stop_the_job(world, broken):
    """Second review: the job must not fail every morning on a file it wrote for itself."""
    world.send(1, STAMP, text="bugword")
    world.answer({"*": verdict()})
    world.state.mkdir(mode=0o700)
    (world.state / "pending.json").write_text(broken)
    assert world.run().returncode == 0
    assert world.read()[f"1/{STAMP}"]["outcome"] == "filed"
    assert json.loads((world.state / "pending.json").read_text()) == {"tries": {}, "half": []}


def test_cron_runs_the_code_of_origin_master(world, tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git is missing")
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    for name in (
        "feedback_triage.py",
        "feedback_model.py",
        "feedback_privacy.py",
        "feedback-cron.sh",
    ):
        shutil.copy2(ROOT / "scripts" / name, repo / "scripts" / name)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "test")
    _git(repo, "config", "user.email", "test@example.org")
    _git(repo, "add", "scripts")
    _git(repo, "-c", "commit.gpgsign=false", "commit", "-qm", "copy")
    _git(repo, "update-ref", "refs/remotes/origin/master", "HEAD")
    # The working copy is not what origin/master holds: the cron job must run the committed one.
    (repo / "scripts" / "feedback_triage.py").write_text("raise SystemExit(9)\n")
    (repo / "scripts" / "feedback-cron.sh").write_text("exit 9\n")
    world.send(1, STAMP, text="bugword")
    world.answer({"*": verdict()})
    # The crontab's own line: the shell file comes from origin/master too.
    line = 'git show origin/master:scripts/feedback-cron.sh | bash -s -- "$@"'
    result = subprocess.run(
        ["bash", "-c", line, "cron", "--data", str(world.data), "--state", str(world.state)],
        capture_output=True,
        text=True,
        timeout=60,
        env=world.env(),
        cwd=repo,
    )
    assert result.returncode == 0, result.stderr
    assert [c[:2] for c in world.writes()] == [["issue", "create"]]
