"""The checks that keep the MCP docs bundle docs/okf/ true to the schema, the server, the recipes
and the evals. Run by mise run lint.

    uv run python scripts/okf_check.py [--docs DIR] [--schema FILE] [--evals DIR] [--tools-src FILE]

Prints one line per problem to stderr and exits 1 when there is any, else exits 0 silently.
"""

import argparse
import contextlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

from blattwerk import schema

ROOT = Path(__file__).resolve().parent.parent
JSON_BLOCK = re.compile(r"```json\n(.*?)\n```", re.S)
ADD_KEYS = {"type", "props", "x", "y", "w", "h"}


def split(path: Path) -> tuple[dict, str]:
    """The frontmatter, empty when the file has none or it does not read, and the body.
    A broken frontmatter is tests/test_okf.py's to report; here `generated` is always a mapping
    and `covers` a list."""
    text = path.read_text()
    found = re.match(r"---\n(.*?)^---$\n?(.*)", text, re.S | re.M)
    if not found:
        return {}, text
    head, body = found.groups()
    try:
        meta = yaml.safe_load(head) if head.strip() else {}
    except yaml.YAMLError:
        meta = {}
    meta = meta if isinstance(meta, dict) else {}
    if not isinstance(meta.get("generated"), dict):
        meta["generated"] = {}
    if not isinstance(meta.get("covers"), list):
        meta["covers"] = []
    return meta, body


def when(value) -> datetime:
    """A generated.at as a time with its offset; none counts as the earliest time."""
    try:
        at = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
    return at if at.tzinfo else at.replace(tzinfo=UTC)


def types_in(doc) -> set:
    """The block types a doc uses; a doc of the wrong shape uses none (check_examples says why)."""
    if not isinstance(doc, dict) or not isinstance(doc.get("pages"), list):
        return set()
    pages = [p for p in doc["pages"] if isinstance(p, dict)]
    blocks = [b for p in pages if isinstance(p.get("blocks"), list) for b in p["blocks"]]
    return {b.get("type") for b in blocks if isinstance(b, dict)}


def resolve(defs: dict, node: dict) -> dict:
    return defs[node["$ref"].split("/")[-1]] if "$ref" in node else node


def block_of(defs: dict, type_: str) -> dict:
    """The schema of one block type: the definition its `if` clause hands the block to."""
    entry = next(
        e for e in defs["Block"]["allOf"] if e["if"]["properties"]["type"]["const"] == type_
    )
    return resolve(defs, entry["then"])


def props_of(defs: dict, type_: str) -> dict:
    return resolve(defs, block_of(defs, type_)["properties"]["props"])


def bare_fields(defs: dict, type_: str) -> list[str]:
    """The fields of a block and of its props that have no description, a block's type aside."""
    block = block_of(defs, type_)
    found = [k for k, v in block["properties"].items() if k != "type" and "description" not in v]
    props = props_of(defs, type_)
    found += [
        f"props.{k}" for k, v in props.get("properties", {}).items() if "description" not in v
    ]
    return found


def json_blocks(body: str) -> list[dict]:
    """The parsed ```json blocks of a body; one that is not JSON is check e's problem, not this."""
    found = []
    for text in JSON_BLOCK.findall(body):
        with contextlib.suppress(ValueError):
            found.append(json.loads(text))
    return found


def check_block_pages(docs: Path, types: list[str]) -> list[str]:
    return [
        f"blocks/{t}.md is missing: the block type {t} has no reference page"
        for t in types
        if not (docs / "blocks" / f"{t}.md").is_file()
    ]


def check_descriptions(defs: dict, types: list[str]) -> list[str]:
    return [
        f"{t}: {f} has no description in the schema" for t in types for f in bare_fields(defs, t)
    ]


def check_how_tos(docs: Path, types: list[str]) -> list[str]:
    allowed = {
        line.split("#")[0].strip()
        for line in (docs / "recipes/no-recipe-yet.txt").read_text().splitlines()
    }
    covered = set()
    for path in sorted((docs / "recipes").glob("*.md")):
        if path.name == "index.md":
            continue
        meta, body = split(path)
        used = set().union(*(types_in(doc) for doc in json_blocks(body)))
        covered |= used & set(meta.get("covers") or [])
    return [
        f"{t} has no how-to in recipes/: write one, or put it on no-recipe-yet.txt on purpose"
        for t in types
        if t not in covered | allowed
    ]


def check_staleness(docs: Path, pages: list[Path]) -> list[str]:
    problems = []
    for path in pages:
        meta, _ = split(path)
        own = when((meta.get("generated") or {}).get("at"))
        for t in meta.get("covers") or []:
            if not (docs / "blocks" / f"{t}.md").is_file():
                continue
            block_meta, _ = split(docs / "blocks" / f"{t}.md")
            changed = when((block_meta.get("generated") or {}).get("at"))
            if changed > own:
                problems.append(
                    f"{path.relative_to(docs)} covers {t}, changed at {changed} "
                    f"after the page's {own}: read the page, fix it, and bump generated.at"
                )
    return problems


def check_examples(defs: dict, files: list[Path], docs: Path) -> list[str]:
    types = defs["Block"]["properties"]["type"]["enum"]
    problems = []
    for path in files:
        for n, text in enumerate(JSON_BLOCK.findall(split(path)[1]), 1):
            where = f"{path.relative_to(docs)}#{n}"
            try:
                example = json.loads(text)
            except ValueError as error:
                problems.append(f"{where}: not JSON: {error}")
                continue
            if isinstance(example, dict) and "pages" in example:
                problems += [f"{where}: {p}" for p in schema.problems(example)]
            elif not (
                isinstance(example, dict)
                and example.get("type") in types
                and set(example) <= ADD_KEYS
            ):
                problems.append(f"{where}: neither a doc nor an add_block call")
            else:
                # add_block takes partial props, so the props schema without its `required`.
                props = props_of(defs, example["type"])
                check = Draft7Validator({**props, "required": [], "definitions": defs})
                problems += [
                    f"{where}: props.{'.'.join(map(str, e.path))}: {e.message}"
                    for e in check.iter_errors(example.get("props", {}))
                ]
    return problems


def keys_in(node) -> set:
    """Every property name a schema names, at any depth."""
    if isinstance(node, list):
        return set().union(*map(keys_in, node)) if node else set()
    if not isinstance(node, dict):
        return set()
    own = set(node["properties"]) if isinstance(node.get("properties"), dict) else set()
    return own.union(*map(keys_in, node.values()))


def check_tool_names(defs: dict, docs: Path, files: list[Path]) -> list[str]:
    snapshot = json.loads((ROOT / "tests/snapshots/mcp_tools.json").read_text())
    tools = {t["name"] for t in snapshot}
    # A snake_case word in backticks is a tool unless it is an argument or a field of a doc.
    known = keys_in(snapshot) | keys_in(defs) | {"okf_version"}
    problems = []
    for path in files:
        words = set(re.findall(r"`([a-z]+(?:_[a-z]+)+)(?:\([^`]*\))?`", path.read_text()))
        for word in sorted(words):
            if word not in tools and word not in known:
                problems.append(
                    f"{path.relative_to(docs)}: names the tool {word}, "
                    "which the server does not have"
                )
    return problems


def check_evals(docs: Path, evals: Path) -> list[str]:
    problems = []
    named = {}
    for path in sorted(evals.glob("*.json")):
        task = json.loads(path.read_text())
        if not re.search(r"mit dem Titel .+ an\.$", task.get("prompt", "")):
            problems.append(f"{path.name}: the prompt must end with 'mit dem Titel <title> an.'")
        if "recipe" in task:
            named[task["recipe"]] = path.name
    stems = {p.stem for p in (docs / "recipes").glob("*.md") if p.name != "index.md"}
    for stem in sorted(stems - set(named)):
        problems.append(
            f'recipes/{stem}.md has no eval task in tests/evals: add one with "recipe": "{stem}"'
        )
    for recipe, name in sorted(named.items()):
        if recipe not in stems:
            problems.append(f"{name}: names the recipe {recipe}, which recipes/ does not have")
    return problems


def check_error_texts(docs: Path, tools_src: Path) -> list[str]:
    page = docs / "tools/errors-and-limits.md"
    if not page.is_file():
        return ["tools/errors-and-limits.md is missing: the server's error texts have no reference"]
    text, src = page.read_text(), tools_src.read_text()
    literals = [
        m.group(2) for m in re.finditer(r"new Fail\(\s*([\"`])((?:\\.|(?!\1).)*?)\1", src, re.S)
    ]
    literals += [m.group(2) for m in re.finditer(r"const TOKEN_MESSAGE = ([\"`])(.*?)\1", src)]
    literals += [
        m.group(2) for m in re.finditer(r"const stale = \(.*?\) =>\s*([`\"])(.*?)\1", src, re.S)
    ]
    problems = []
    for literal in literals:
        # The fixed pieces of a message, between its ${ values; a short piece says too little.
        for piece in re.split(r"\$\{[^}]*\}", literal.replace('\\"', '"').replace("\\n", "\n")):
            piece = piece.strip()
            if len(piece) >= 12 and piece not in text:
                problems.append(
                    f'tools/errors-and-limits.md lacks the error text "{piece}" from tools.ts'
                )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--docs", type=Path, default=ROOT / "docs/okf")
    parser.add_argument("--schema", type=Path, default=ROOT / "src/blattwerk/sheet.schema.json")
    parser.add_argument("--evals", type=Path, default=ROOT / "tests/evals")
    parser.add_argument("--tools-src", type=Path, default=ROOT / "frontend/mcp/tools.ts")
    args = parser.parse_args(argv)

    docs = args.docs
    defs = json.loads(args.schema.read_text())["definitions"]
    types = defs["Block"]["properties"]["type"]["enum"]
    files = sorted(docs.rglob("*.md"))
    hand = [
        f for f in files if f.name != "index.md" and split(f)[0] and f.parent != docs / "blocks"
    ]

    problems = [
        *check_block_pages(docs, types),
        *check_descriptions(defs, types),
        *check_how_tos(docs, types),
        *check_staleness(docs, hand),
        *check_examples(defs, files, docs),
        *check_tool_names(defs, docs, files),
        *check_evals(docs, args.evals),
        *check_error_texts(docs, args.tools_src),
    ]
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
