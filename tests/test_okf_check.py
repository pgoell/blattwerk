"""scripts/okf_check.py: each check fails on a planted stale doc, and passes on the repo."""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/okf"
SCHEMA = ROOT / "src/blattwerk/sheet.schema.json"
EVALS = ROOT / "tests/evals"


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    folder = tmp_path / "okf"
    shutil.copytree(DOCS, folder)
    return folder


def check(docs: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "scripts/okf_check.py", "--docs", str(docs), *extra],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert old in text, f"{path.name} lacks {old!r}"
    path.write_text(text.replace(old, new, 1))


def test_a_block_type_without_its_page(docs: Path):
    (docs / "blocks/uhr.md").unlink()
    result = check(docs)
    assert result.returncode == 1
    assert "blocks/uhr.md is missing" in result.stderr


def test_a_prop_without_a_description(tmp_path: Path, docs: Path):
    schema = json.loads(SCHEMA.read_text())
    defs = schema["definitions"]
    props = defs["UhrBlock"]["properties"]["props"]
    if "$ref" in props:
        props = defs[props["$ref"].split("/")[-1]]
    name = next(iter(props["properties"]))
    del props["properties"][name]["description"]
    copy = tmp_path / "sheet.schema.json"
    copy.write_text(json.dumps(schema))
    result = check(docs, "--schema", str(copy))
    assert result.returncode == 1
    assert f"uhr: props.{name} has no description" in result.stderr


def test_a_type_without_a_how_to(docs: Path):
    (docs / "recipes/uhrzeiten-lesen.md").unlink()
    index = docs / "recipes/index.md"
    lines = [
        line
        for line in index.read_text().splitlines(keepends=True)
        if "(uhrzeiten-lesen.md)" not in line
    ]
    index.write_text("".join(lines))
    result = check(docs)
    assert result.returncode == 1
    assert "uhr has no how-to in recipes/" in result.stderr


def test_a_how_to_older_than_its_block_page(docs: Path):
    uhr = docs / "blocks/uhr.md"
    text = uhr.read_text()
    uhr.write_text(
        re.sub(
            r"(?m)^generated: .*$",
            'generated: { by: "process:frontend/okf.mjs", at: 2099-01-01T00:00:00Z }',
            text,
            count=1,
        )
    )
    result = check(docs)
    assert result.returncode == 1
    assert "recipes/uhrzeiten-lesen.md covers uhr" in result.stderr
    assert "read the page, fix it, and bump generated.at" in result.stderr


def test_an_example_doc_that_breaks_the_schema(docs: Path):
    edit(docs / "recipes/uhrzeiten-lesen.md", '"x": 15', '"x": "links"')
    result = check(docs)
    assert result.returncode == 1
    assert "recipes/uhrzeiten-lesen.md#1" in result.stderr


def test_a_tool_the_server_does_not_have(docs: Path):
    recipe = docs / "recipes/uhrzeiten-lesen.md"
    recipe.write_text(recipe.read_text() + "\nCall `add_picture` first.\n")
    result = check(docs)
    assert result.returncode == 1
    assert "names the tool add_picture, which the server does not have" in result.stderr


@pytest.mark.parametrize("named", ["`make_sheet`", "`add_picture(svg)`"])
def test_a_tool_of_any_name_the_server_does_not_have(docs: Path, named: str):
    recipe = docs / "recipes/uhrzeiten-lesen.md"
    recipe.write_text(recipe.read_text() + f"\nCall {named} first.\n")
    result = check(docs)
    assert result.returncode == 1
    tool = named.strip("`").split("(")[0]
    assert f"names the tool {tool}, which the server does not have" in result.stderr


def test_an_add_block_example_with_wrong_props(docs: Path):
    edit(
        docs / "blocks/uhr.md",
        '{"type": "uhr", "props": {}}',
        '{"type": "uhr", "props": {"count": "viele"}}',
    )
    result = check(docs)
    assert result.returncode == 1
    assert "blocks/uhr.md#1: props.count:" in result.stderr


@pytest.mark.parametrize(
    "text",
    [
        "# Notes\n",
        "---\ntitle: open\n",
        "---\n---\n",
        "---\ntype: How-to\ncovers: [uhr]\n---\n\n```json\n[1, 2]\n```\n",
        '---\ntype: How-to\ncovers: [uhr]\n---\n\n```json\n{"pages": [{}]}\n```\n',
        "---\ntitle: [x\n---\nbody\n",
        "---\ntitle: x\n\nSome text: a: b\n\n---\n\nbody\n",
        "---\ngenerated: soon\ncovers: text\n---\nbody\n",
    ],
    ids=[
        *["no-frontmatter", "not-closed", "empty", "a-list", "a-page-without-blocks"],
        *["bad-yaml", "not-closed-with-a-rule-below", "fields-of-the-wrong-kind"],
    ],
)
def test_an_odd_doc_gives_a_message_not_a_crash(docs: Path, text: str):
    (docs / "recipes/odd.md").write_text(text)
    result = check(docs)
    assert "Traceback" not in result.stderr, result.stderr
    assert result.returncode == 1


def test_a_recipe_without_an_eval_task(tmp_path: Path, docs: Path):
    evals = tmp_path / "evals"
    shutil.copytree(EVALS, evals)
    named = next(p for p in sorted(evals.glob("*.json")) if "recipe" in json.loads(p.read_text()))
    task = json.loads(named.read_text())
    stem = task.pop("recipe")
    named.write_text(json.dumps(task, ensure_ascii=False, indent=2))
    result = check(docs, "--evals", str(evals))
    assert result.returncode == 1
    assert f"recipes/{stem}.md has no eval task" in result.stderr


# One text from TOKEN_MESSAGE, one from a `new Fail(...)`, one from `stale`.
@pytest.mark.parametrize(
    "words", ["token is not valid", "is locked. Nothing was written.", "since you read it"]
)
def test_an_error_text_missing_from_the_reference(docs: Path, words: str):
    page = docs / "tools/errors-and-limits.md"
    lines = [line for line in page.read_text().splitlines(keepends=True) if words not in line]
    page.write_text("".join(lines))
    result = check(docs)
    assert result.returncode == 1
    assert words in result.stderr


def test_the_checks_pass_on_the_repo():
    result = subprocess.run(
        [sys.executable, "scripts/okf_check.py"], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
