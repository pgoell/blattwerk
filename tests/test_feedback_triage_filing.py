"""Triage files a bug or a wish once, comments on a match, and labels an MCP send as AI."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import json

import pytest
from test_feedback_triage import (
    PIC,
    ROOT,
    STAMP,
    chmod_tree,
    section,
    tree,
    value,
    verdict,
    world,  # noqa: F401
)


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


@pytest.mark.parametrize("kind", ["bug", "wish"])
def test_mcp_send_labels_ai(world, kind):
    world.send(1, STAMP, text="bugword", extra={"source": "mcp"})
    world.answer({"*": verdict(kind, title="Undo loses page", body="Steps here.")})
    assert world.run().returncode == 0
    (create,) = world.writes()
    labels = [create[i + 1] for i, arg in enumerate(create) if arg == "--label"]
    assert labels == ["feedback", kind, "ai"]
    body = value(create, "--body")
    assert "From an AI's feedback" in body and "restated by the daily feedback job" in body


def test_teacher_send_has_no_ai_label(world):
    world.send(1, STAMP, text="bugword")
    world.answer({"*": verdict("bug", title="Undo loses page", body="Steps here.")})
    assert world.run().returncode == 0
    (create,) = world.writes()
    labels = [create[i + 1] for i, arg in enumerate(create) if arg == "--label"]
    assert labels == ["feedback", "bug"]
    assert "From a teacher's feedback" in value(create, "--body")


def test_mcp_send_comment_says_ai(world):
    world.send(1, STAMP, text="bugword", extra={"source": "mcp"})
    world.answer({"*": verdict(issue=12)})
    result = world.run(GH_ISSUES=json.dumps([{"number": 12, "title": "Undo"}]))
    assert result.returncode == 0, result.stderr
    (comment,) = world.writes()
    assert comment[:3] == ["issue", "comment", "12"]
    assert value(comment, "--body").startswith("An AI working through the MCP reports")


def test_mcp_send_naming_feedback_and_blattomat_is_filed(world):
    # The head and footer the job adds must not hit a word the AI's send holds.
    text = "Ich sende dieses Feedback: Blattomat zeichnet die Zeiger falsch."
    world.send(1, STAMP, text=text, extra={"source": "mcp"})
    world.answer({"*": verdict(issue=12, body="Blattomat draws the clock hands wrong.")})
    result = world.run(GH_ISSUES=json.dumps([{"number": 12, "title": "Clock"}]))
    assert result.returncode == 0, result.stderr
    assert world.read()[f"1/{STAMP}"]["outcome"] == "commented"


@pytest.mark.parametrize(
    "text, body, reason",
    [
        (
            "The heading Lisa rechnet draws twice",
            "Lisa's heading draws twice.",
            "word from the send",
        ),
        (
            "zehn Äpfel und drei Birnen kosten",
            "Steps: zehn Äpfel und drei Birnen kosten, see above.",
            "copied words",
        ),
    ],
    ids=["name", "copied"],
)
def test_mcp_send_with_sheet_text_or_name_is_refused(world, text, body, reason):
    world.send(1, STAMP, text=text, extra={"source": "mcp"})
    world.answer({"*": verdict(body=body)})
    assert world.run().returncode == 0
    assert world.writes() == []
    assert world.read()[f"1/{STAMP}"]["outcome"] == "refused"
    assert reason in section(world.summary(), "Left for Pascal")


def test_mcp_send_prompt_names_the_ai_not_the_sheet(world):
    world.send(1, STAMP, text="bugword", seite=None, extra={"source": "mcp", "sheet_id": "4711"})
    world.answer({"*": verdict("nothing")})
    assert world.run().returncode == 0
    stdin = world.claude_calls()[0]["stdin"]
    assert "Sent by: an AI model" in stdin
    assert "The AI's text, between the markers:" in stdin
    assert "/blatt/N" in stdin
    assert "4711" not in stdin


def test_readme_names_mcp_sends_and_the_ai_label():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section_text = readme.split("### The daily feedback job\n")[1].split("\n### ")[0]
    assert "MCP" in section_text and "`ai`" in section_text


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
