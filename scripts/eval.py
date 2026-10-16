"""The teacher tasks in tests/evals, run by Claude through the Blattomat MCP server, and scored.

    uv run python scripts/eval.py                 # all tasks
    uv run python scripts/eval.py plus_bis_20     # named tasks

Each tests/evals/<name>.json holds a German prompt and what the sheet must hold. The prompt
names the sheet's title; each task runs `claude -p` headless on the Claude subscription, with the
MCP server of a local app on a fresh data folder. Not for CI: it spends the subscription.
"""

import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from blattwerk import db, schema

sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))
import ui  # ty: ignore[unresolved-import]

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "tests" / "evals"
OUT = ROOT / "eval-out"
MCP = ROOT / "frontend" / "mcp" / "stdio.ts"  # the Blattomat MCP server, run by node
MARGIN = 15
TOLERANCE = 0.5
PAPER = {False: (210, 297), True: (297, 210)}  # landscape: (width, height) in mm
SYSTEM = (
    "Use only the blattomat tools. Read the docs resources before you build the sheet. "
    "Check the layout with render_preview before you finish."
)


def layout_problems(doc: dict) -> list[str]:
    """Each block lies within the margin, and no two blocks on one page meet."""
    problems = []
    for number, page in enumerate(doc.get("pages", []), 1):
        width, height = PAPER[bool(page.get("landscape", doc.get("landscape", False)))]
        rects = {}
        for index, block in enumerate(page.get("blocks", []), 1):
            name = f"page {number} block {index} ({block.get('type')})"
            rects[name] = tuple(block.get(k, 0) for k in ("x", "y", "w", "h"))
        for name, (x, y, w, h) in rects.items():
            if x < MARGIN - TOLERANCE:
                problems.append(f"{name}: {x} mm from the left edge")
            if y < MARGIN - TOLERANCE:
                problems.append(f"{name}: {y} mm from the top edge")
            if x + w > width - MARGIN + TOLERANCE:
                problems.append(f"{name}: past the right margin")
            if y + h > height - MARGIN + TOLERANCE:
                problems.append(f"{name}: past the bottom margin")
        names = list(rects)
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                ax, ay, aw, ah = rects[a]
                bx, by, bw, bh = rects[b]
                if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                    problems.append(f"{a} and {b} overlap")
    return problems


def missing(doc: dict, expect: dict) -> list[str]:
    """The block types and words the doc lacks; words match in any string, any case."""
    types = {b.get("type") for page in doc.get("pages", []) for b in page.get("blocks", [])}
    text = json.dumps(doc, ensure_ascii=False).lower()
    return [t for t in expect["types"] if t not in types] + [
        w for w in expect["text"] if w.lower() not in text
    ]


def run_claude(prompt: str, config: Path, cwd: Path) -> dict:
    command = [
        "claude", "-p", prompt,
        "--mcp-config", str(config), "--strict-mcp-config",
        "--allowedTools", "mcp__blattomat__*",
        "--max-turns", "40", "--output-format", "json",
        "--append-system-prompt", SYSTEM,
    ]  # fmt: skip
    try:
        done = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return {"error": "timeout after 600 s"}
    try:
        return json.loads(done.stdout)
    except json.JSONDecodeError:
        return {"error": f"exit {done.returncode}: {done.stderr[-300:]}"}


def find_doc(client, title: str) -> dict | None:
    for row in client.get("/api/sheets").json():
        if row["title"] == title:
            return client.get(f"/api/sheets/{row['id']}").json()["doc"]
    return None


def main(names: list[str]) -> int:
    known = sorted(p.stem for p in TASKS.glob("*.json"))
    unknown = [n for n in names if n not in known]
    if unknown:
        print(f"no task {', '.join(unknown)}; the tasks are {', '.join(known)}", file=sys.stderr)
        return 2
    chosen = names or known
    tasks = {n: json.loads((TASKS / f"{n}.json").read_text()) for n in chosen}
    # Before the first user: the database is made where this points.
    db.DATA_DIR = Path(tempfile.mkdtemp())
    workdir = Path(tempfile.mkdtemp())
    with ui.serving() as base:
        if not base.startswith("http://127.0.0.1:"):
            print(f"refusing to run against {base}: only 127.0.0.1", file=sys.stderr)
            return 2
        client = ui.user()
        token = client.post("/api/tokens", json={"name": "eval"}).json()["token"]
        config = workdir / "mcp.json"
        server = {
            "command": "node",
            "args": [str(MCP)],
            "env": {"BLATTWERK_URL": base, "BLATTWERK_TOKEN": token},
        }
        config.write_text(json.dumps({"mcpServers": {"blattomat": server}}))
        with ThreadPoolExecutor(max_workers=4) as pool:
            runs = list(pool.map(lambda n: run_claude(tasks[n]["prompt"], config, workdir), chosen))

        rows, notes = [], []
        for name, run in zip(chosen, runs, strict=True):
            title = tasks[name]["prompt"].rsplit("mit dem Titel ", 1)[1].removesuffix(" an.")
            doc = find_doc(client, title)
            if doc is None:
                checks = [False, False, False, False]
                notes.append(f"{name}: no sheet titled {title!r}; {run.get('error', '')}")
            else:
                wrong = missing(doc, tasks[name]["expect"])
                schema_faults = schema.problems(doc)
                layout = layout_problems(doc)
                checks = [True, not schema_faults, not layout, not wrong]
                for label, faults in [
                    ("schema", schema_faults),
                    ("layout", layout),
                    ("missing", wrong),
                ]:
                    if faults:
                        notes.append(f"{name}: {label}: {'; '.join(map(str, faults[:3]))}")
                if "error" in run:
                    notes.append(f"{name}: {run['error']}")
            rows.append((name, checks, run))

    lines = [
        "| task | created | valid | no overlap | holds | score | turns | cost |",
        "|---|---|---|---|---|---|---|---|",
    ]
    scores = []
    for name, checks, run in rows:
        score = sum(checks) / 4
        scores.append(score)
        cost = run.get("total_cost_usd")
        lines.append(
            f"| {name} | "
            + " | ".join("yes" if c else "no" for c in checks)
            + f" | {score:.2f} | {run.get('num_turns', '-')} | "
            + (f"{cost:.2f} USD" if cost is not None else "-")
            + " |"
        )
    lines.append(f"| **mean** | | | | | **{sum(scores) / len(scores):.2f}** | | |")
    text = "\n".join(lines) + "\n"
    if notes:
        text += "\n" + "\n".join(f"- {note}" for note in notes) + "\n"
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{datetime.now():%Y-%m-%d-%H%M%S}.md"
    path.write_text(text)
    print(text)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
