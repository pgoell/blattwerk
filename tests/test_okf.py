"""The docs bundle docs/okf/ keeps the shape of the Open Knowledge Format v0.2: concepts with
frontmatter, index files without, and links that land on a file of the bundle."""

import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs/okf"
SCHEMA = json.loads((ROOT / "src/blattwerk/sheet.schema.json").read_text())
TYPES = SCHEMA["definitions"]["Block"]["properties"]["type"]["enum"]
# The Diátaxis kind of each folder's concepts.
KINDS = {"": "Explanation", "blocks": "Reference", "recipes": "How-to", "tutorials": "Tutorial"}
FILES = sorted(DOCS.rglob("*.md"))
CONCEPTS = [f for f in FILES if f.name != "index.md"]
INDEXES = [f for f in FILES if f.name == "index.md"]


def split(path: Path) -> tuple[dict | None, str]:
    """The frontmatter, None when the file has none, and the body."""
    text = path.read_text()
    if not text.startswith("---\n"):
        return None, text
    head, body = text[4:].split("\n---\n", 1)
    return yaml.safe_load(head), body


def name(path: Path) -> str:
    return str(path.relative_to(DOCS))


def test_the_bundle_has_the_folders_of_the_issue():
    for path in ("index.md", "page-model.md", "blocks/index.md", "recipes/index.md"):
        assert (DOCS / path).is_file(), path
    assert [f for f in CONCEPTS if f.parent.name == "recipes"]
    assert [f for f in CONCEPTS if f.parent.name == "tutorials"]


@pytest.mark.parametrize("path", CONCEPTS, ids=name)
def test_a_concept_has_okf_frontmatter(path):
    meta, body = split(path)
    assert meta is not None, "a concept starts with frontmatter"
    folder = str(path.parent.relative_to(DOCS)).replace(".", "")
    assert meta["type"] == KINDS[folder]
    for key in ("title", "description"):
        assert isinstance(meta[key], str) and meta[key]
    assert isinstance(meta["tags"], list) and meta["tags"]
    assert set(meta["covers"]) <= set(TYPES)
    # v0.2: `generated.by` names who wrote it; `at`, when there, is a datetime with its offset.
    assert meta["generated"]["by"].startswith(("human:", "process:"))
    if "at" in meta["generated"]:
        assert re.fullmatch(
            r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ",
            str(meta["generated"]["at"]).replace(" ", "T").replace("+00:00", "Z"),
        )
    assert body.strip()


@pytest.mark.parametrize("path", INDEXES, ids=name)
def test_an_index_has_no_frontmatter_but_the_roots_version(path):
    meta, _ = split(path)
    if path == DOCS / "index.md":
        assert meta == {"okf_version": "0.2"}
    else:
        assert meta is None


@pytest.mark.parametrize("path", INDEXES, ids=name)
def test_an_index_lists_every_file_and_folder_beside_it(path):
    _, body = split(path)
    links = set(re.findall(r"^\* \[[^\]]+\]\(([^)]+)\)", body, re.M))
    beside = {f.name for f in path.parent.glob("*.md") if f.name != "index.md"}
    beside |= {f"{d.name}/index.md" for d in path.parent.iterdir() if d.is_dir()}
    assert beside <= links


@pytest.mark.parametrize("path", INDEXES, ids=name)
def test_an_index_line_carries_the_concepts_description(path):
    _, body = split(path)
    for target, said in re.findall(r"^\* \[[^\]]+\]\(([^)]+\.md)\): (.+)$", body, re.M):
        meta, _ = split(path.parent / target)
        if meta and "description" in meta:
            assert said == meta["description"], target


@pytest.mark.parametrize("path", FILES, ids=name)
def test_every_link_lands_on_a_file_of_the_bundle(path):
    _, body = split(path)
    # Code blocks hold JSON, not links.
    prose = re.sub(r"```.*?```", "", body, flags=re.S)
    for target in re.findall(r"\]\(([^)\s]+)\)", prose):
        if re.match(r"https?://", target):
            continue
        assert (path.parent / target.split("#")[0]).resolve().is_file(), f"{name(path)}: {target}"


def when(value) -> str:
    """A generated.at as the text it is written in, so that times compare as text."""
    return str(value).replace(" ", "T").replace("+00:00", "Z")


HAND_PAGES = [f for f in CONCEPTS if f.parent != DOCS / "blocks"]


@pytest.mark.parametrize("path", HAND_PAGES, ids=name)
def test_a_page_is_newer_than_the_blocks_it_covers(path):
    meta, _ = split(path)
    assert meta is not None
    own = when(meta["generated"]["at"])
    for block_type in meta["covers"]:
        block_meta, _ = split(DOCS / "blocks" / f"{block_type}.md")
        assert block_meta is not None
        changed = when(block_meta["generated"]["at"])
        assert changed <= own, (
            f"{name(path)} covers {block_type}, changed at {changed} after the page's {own}: "
            "read the page, fix it, and bump generated.at"
        )


def test_the_index_states_one_language_rule():
    _, body = split(DOCS / "index.md")
    rule = next(line for line in body.splitlines() if line.startswith("Language:"))
    assert "German" in rule and "English" in rule


def test_the_index_stays_short():
    # It is the server's instructions: Claude reads it on every start.
    assert len((DOCS / "index.md").read_text()) < 3000


def test_the_tutorial_names_what_the_teacher_does_herself():
    _, body = split(DOCS / "tutorials/dein-erstes-blatt-mit-claude.md")
    # The account page's own words (frontend/src/pages/Account.tsx).
    for words in ("Konto", "Zugang für Claude", "Schlüssel erstellen", "Kopieren", "Widerrufen"):
        assert words in body
    assert "claude.ai/download" in body
    account = (ROOT / "frontend/src/pages/Account.tsx").read_text()
    # The install (#653): the link on the account page, and the file it gives.
    assert "Erweiterung für Claude Desktop herunterladen" in body
    assert "Erweiterung für Claude Desktop herunterladen" in account
    assert 'download="blattomat.mcpb"' in account and "`blattomat.mcpb`" in body
    # The key's name field is empty, the example in its label (#737); an empty name makes no key.
    assert 'useState("")' in account and "placeholder" not in account
    assert "Name des Schlüssels, z. B. Laptop Schule" in account
    assert "**Name des Schlüssels**" in body
    assert "schreib einen Namen in das Feld" in body
