"""The OKF block reference pages match the sheet's JSON Schema."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = ROOT / "docs" / "okf" / "blocks"
SCHEMA = ROOT / "src" / "blattwerk" / "sheet.schema.json"


def block_types() -> list[str]:
    schema = json.loads(SCHEMA.read_text())
    return schema["definitions"]["Block"]["properties"]["type"]["enum"]


def props_of(block_type: str) -> list[str]:
    """Prop names of one block type, read from the schema."""
    schema = json.loads(SCHEMA.read_text())
    defs = schema["definitions"]
    for branch in defs["Block"]["allOf"]:
        if branch["if"]["properties"]["type"]["const"] == block_type:
            ref = branch["then"]["$ref"].rsplit("/", 1)[1]
            block = defs[ref]
            props = block["properties"]["props"]
            if "$ref" in props:
                props = defs[props["$ref"].rsplit("/", 1)[1]]
            return list(props.get("properties", {}))
    raise AssertionError(f"no schema branch for {block_type}")


def check(folder: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", "frontend/okf.mjs", "--check", "--dir", str(folder)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def pages(tmp_path: Path) -> Path:
    folder = tmp_path / "blocks"
    shutil.copytree(BLOCKS, folder)
    return folder


def test_a_page_per_block_type():
    types = block_types()
    assert len(types) == 19
    index = (BLOCKS / "index.md").read_text()
    for block_type in types:
        assert (BLOCKS / f"{block_type}.md").is_file(), block_type
        assert f"({block_type}.md)" in index, block_type


def test_check_passes_on_the_checked_in_pages(pages: Path):
    result = check(pages)
    assert result.returncode == 0, result.stdout + result.stderr


def test_check_fails_on_a_changed_page(pages: Path):
    maths = pages / "maths.md"
    lines = maths.read_text().splitlines(keepends=True)
    lines[-1] = lines[-1] + "\nA stray line.\n"
    maths.write_text("".join(lines))
    result = check(pages)
    assert result.returncode == 1
    assert "maths.md" in result.stdout + result.stderr


def test_check_fails_on_a_missing_page(pages: Path):
    (pages / "uhr.md").unlink()
    result = check(pages)
    assert result.returncode == 1
    assert "uhr.md" in result.stdout + result.stderr


def test_check_fails_on_an_extra_page(pages: Path):
    (pages / "extra.md").write_text("# Extra\n")
    result = check(pages)
    assert result.returncode == 1
    assert "extra.md" in result.stdout + result.stderr


@pytest.mark.parametrize("block_type", block_types())
def test_every_prop_has_a_row(block_type: str):
    text = (BLOCKS / f"{block_type}.md").read_text()
    for prop in props_of(block_type):
        assert f"| `{prop}` |" in text or f"| {prop} |" in text, prop
