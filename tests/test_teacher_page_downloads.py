"""The teacher-page tool tidies downloads, closes tabs and drops the session."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

from contextlib import contextmanager

import pytest
from playwright.sync_api import expect
from test_teacher_page import (
    ONE,
    folder,  # noqa: F401
    pytestmark,  # noqa: F401
    run,
    tool,
)
from ui import (
    at,
    box,
)

# The downloads, the session and the boxes


def test_tidy_deletes_the_tr_pdfs_in_downloads_and_nothing_else(
    folder, server, tmp_path, monkeypatch
):
    downloads = tmp_path / "downloads"
    (downloads / "sub").mkdir(parents=True)
    monkeypatch.setenv("TEACHER_PAGE_DOWNLOADS", str(downloads))
    for name in ("TR1 Rechnen.pdf", "TR2.pdf", "TR1.png", "Other.pdf", "sub/TR4.pdf"):
        (downloads / name).write_bytes(b"%PDF")
    (downloads / "TR3.pdf").mkdir()

    done = run(folder, server, "tidy")
    assert (done.returncode, done.stderr) == (0, "")
    assert sorted(done.stdout.splitlines()) == [
        "deleted downloads/TR1 Rechnen.pdf",
        "deleted downloads/TR2.pdf",
    ]
    kept = sorted(str(path.relative_to(downloads)) for path in downloads.rglob("*"))
    assert kept == ["Other.pdf", "TR1.png", "TR3.pdf", "sub", "sub/TR4.pdf"]
    assert run(folder, server, "tidy").stdout == "nothing to delete\n"


def test_tidy_deletes_the_blattomat_extension_download_and_names_it(
    folder, server, tmp_path, monkeypatch
):
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    monkeypatch.setenv("TEACHER_PAGE_DOWNLOADS", str(downloads))
    (downloads / "blattomat.mcpb").write_bytes(b"zip")
    (downloads / "other.mcpb").write_bytes(b"zip")

    done = run(folder, server, "tidy")
    assert (done.returncode, done.stderr) == (0, "")
    assert done.stdout == "deleted downloads/blattomat.mcpb\n"
    assert [path.name for path in downloads.iterdir()] == ["other.mcpb"]


def test_tidy_deletes_the_pdfs_that_pdf_saved_in_the_tool_folder(
    folder, server, tmp_path, monkeypatch
):
    # Issue #430: `pdf` saves into the tool's folder, and `tidy` left those files behind.
    monkeypatch.setenv("TEACHER_PAGE_DOWNLOADS", str(tmp_path / "empty"))
    (tmp_path / "empty").mkdir()
    (folder / "Blatt 3.pdf").write_bytes(b"%PDF")
    (folder / "last.png").write_bytes(b"png")

    done = run(folder, server, "tidy")
    assert (done.returncode, done.stderr) == (0, "")
    assert done.stdout == f"deleted {folder.name}/Blatt 3.pdf\n"
    assert [path.name for path in folder.iterdir()] == ["last.png"]


def test_close_tabs_shuts_a_tab_the_page_opened_and_names_it(editor):
    page = editor(box("a", "text", ONE))
    with page.context.expect_page() as new:
        page.evaluate("window.open('about:blank')")
    opened = new.value
    lines = tool.close_tabs(page)
    assert len(lines) == 1
    assert "about:blank" in lines[0]
    assert opened.is_closed()
    assert not page.is_closed()


def test_a_verb_that_fails_after_a_tab_opened_still_closes_the_tab(editor, monkeypatch):
    """Review of #738: a tab left open would be the next verb's page, so a failure closes it too."""
    page = editor(box("a", "text", ONE))

    @contextmanager
    def joined():
        yield page

    def fails(page):
        with page.context.expect_page():
            page.evaluate("window.open('about:blank')")
        raise tool.Refused("failed after the click")

    monkeypatch.setattr(tool, "joined", joined)
    monkeypatch.setitem(tool.VERBS, "fails", fails)
    with pytest.raises(tool.Refused, match="failed after the click"):
        tool.verb("fails", (), False)
    assert page.context.pages == [page]


def test_expire_drops_the_session_and_the_page_stays(editor):
    page = editor(box("a", "text", ONE))
    said = tool.expire(page)
    assert said.startswith("the session has run out: ")
    expect(at(page, "a")).to_be_visible()
    tool.go(page, "/")
    expect(page.get_by_role("button", name="Anmelden", exact=True)).to_be_visible()
