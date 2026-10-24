"""Voice, pictures and the day's summary say what was filed and what was only kept to hear."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import json

from test_feedback_triage import (
    PIC,
    STAMP,
    section,
    verdict,
    world,  # noqa: F401
)


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
