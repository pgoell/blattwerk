"""Every block type has its descriptions, its docs page and its MCP tool entry, and a recipe or
a place on the allow list. The tool list is kept in tests/snapshots/mcp_tools.json."""

import json
import os
import re
from pathlib import Path

import pytest
from test_mcp import start

ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs/okf"
RECIPES = DOCS / "recipes"
ALLOW = RECIPES / "no-recipe-yet.txt"
SNAPSHOT = ROOT / "tests/snapshots/mcp_tools.json"
DEFS = json.loads((ROOT / "src/blattwerk/sheet.schema.json").read_text())["definitions"]
TYPES = DEFS["Block"]["properties"]["type"]["enum"]


def resolve(node):
    """The definition a $ref names, or the node itself."""
    if "$ref" in node:
        return DEFS[node["$ref"].split("/")[-1]]
    return node


def block_def(type_):
    """The schema of one block type: the definition its `if` clause hands the block to."""
    entry = next(
        e for e in DEFS["Block"]["allOf"] if e["if"]["properties"]["type"]["const"] == type_
    )
    return resolve(entry["then"])


def bare_fields(type_):
    """The fields of a block and of its props that have no description, a block's type aside."""
    block = block_def(type_)
    found = [k for k, v in block["properties"].items() if k != "type" and "description" not in v]
    props = resolve(block["properties"]["props"])
    found += [
        f"props.{k}" for k, v in props.get("properties", {}).items() if "description" not in v
    ]
    return found


def allowed():
    """The types on the allow list: one per line, `#` starts a comment."""
    lines = (line.split("#")[0].strip() for line in ALLOW.read_text().splitlines())
    return {line for line in lines if line}


def used_by_recipes():
    found = set()
    for path in sorted(RECIPES.glob("*.md")):
        if path.name == "index.md":
            continue
        text = path.read_text()
        block = re.search(r"```json\n(.*?)\n```", text, re.S)
        assert block, f"{path.name} has no json block"
        for page in json.loads(block[1])["pages"]:
            found |= {b["type"] for b in page["blocks"]}
    return found


def add_block_types(server, tmp_path):
    _, mcp = start(server, tmp_path)
    try:
        tools = mcp.tools()
    finally:
        mcp.stop()
    add = next(t for t in tools if t["name"] == "add_block")
    return add["inputSchema"]["properties"]["type"]["enum"]


@pytest.mark.parametrize("type_", TYPES)
def test_block_fields_have_descriptions(type_):
    assert bare_fields(type_) == []


@pytest.mark.parametrize("type_", TYPES)
def test_block_has_a_docs_page(type_):
    assert (DOCS / "blocks" / f"{type_}.md").is_file()


@pytest.mark.parametrize("type_", TYPES)
def test_add_block_offers_the_type(server, tmp_path, type_):
    assert type_ in add_block_types(server, tmp_path)


@pytest.mark.parametrize("type_", TYPES)
def test_type_has_a_recipe_or_is_allowed_not_to(type_):
    assert type_ in used_by_recipes() or type_ in allowed(), (
        f"{type_} has no recipe in docs/okf/recipes and is not on {ALLOW.name}: "
        "write a recipe, or add it there on purpose"
    )


def test_allow_list_shrinks_when_a_recipe_uses_its_type():
    used = sorted(allowed() & used_by_recipes())
    assert used == [], f"these now have a recipe: remove them from {ALLOW.name}: {used}"


def test_allow_list_names_only_real_types():
    unknown = sorted(allowed() - set(TYPES))
    assert unknown == [], f"not block types in the schema, remove from {ALLOW.name}: {unknown}"


def test_tool_snapshot(server, tmp_path):
    _, mcp = start(server, tmp_path)
    try:
        tools = mcp.tools()
    finally:
        mcp.stop()
    picked = [
        {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}
        for t in sorted(tools, key=lambda t: t["name"])
    ]
    text = json.dumps(picked, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if os.environ.get("BLATTWERK_SNAPSHOT") == "update":
        SNAPSHOT.write_text(text)
        return
    was = SNAPSHOT.read_text() if SNAPSHOT.exists() else ""
    assert was == text, (
        "the MCP tool list differs from tests/snapshots/mcp_tools.json. If the change is meant, "
        "update it with: BLATTWERK_SNAPSHOT=update mise run test:one -- "
        "tests/test_mcp_coverage.py::test_tool_snapshot"
    )
