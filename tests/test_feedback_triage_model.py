"""A bad model answer or a failed GitHub write is retried, and the model gets no tools."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import json

import pytest
from test_feedback_triage import (
    BAD_VERDICTS,
    PIC,
    STAMP,
    value,
    verdict,
    world,  # noqa: F401
)


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
    assert "Run failed" in world.summary()


def test_failed_issue_list_says_so_on_summary(world):
    world.send(1, STAMP, text="bugword")
    world.answer({"*": verdict()})
    result = world.run(GH_RC_LIST="1")
    assert result.returncode == 1
    assert world.claude_calls() == []
    assert f"1/{STAMP}" not in world.read()
    assert "Run failed" in world.summary()


def test_dry_run_failure_writes_nothing(world):
    world.send(1, STAMP, text="bugword")
    (world.data / "blattwerk.db").unlink()
    result = world.run("--dry-run")
    assert result.returncode == 1
    assert not world.state.exists()


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
