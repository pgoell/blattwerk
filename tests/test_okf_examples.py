"""Every ```json example in docs/okf renders: a doc as a preview, an add_block call on a sheet."""

import json
import re
from pathlib import Path

import httpx
import pytest
from test_mcp import start
from ui import user

DOCS = Path(__file__).resolve().parents[1] / "docs/okf"
PICTURE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
    '<rect width="10" height="10"/></svg>'
)


def examples():
    for path in sorted(DOCS.rglob("*.md")):
        for n, text in enumerate(re.findall(r"```json\n(.*?)\n```", path.read_text(), re.S), 1):
            yield pytest.param(text, id=f"{path.relative_to(DOCS)}#{n}")


@pytest.mark.parametrize("text", list(examples()))
def test_an_example_renders(text, server, tmp_path):
    example = json.loads(text)
    if "pages" in example:
        client = user()
        preview = httpx.post(
            f"{server}/api/preview.png",
            json={"doc": example},
            headers={"Cookie": f"session={client.cookies['session']}"},
            timeout=60,
        )
        assert preview.status_code == 200, preview.text
        return

    _, mcp = start(server, tmp_path)
    try:
        sheet = json.loads(mcp.call("create_sheet", title="Beispiel")["content"][0]["text"])
        props = dict(example.get("props", {}))
        if example["type"] == "image":
            picture = mcp.call("upload_picture", svg=PICTURE)
            props["upload"] = json.loads(picture["content"][0]["text"])["upload"]
        args = {"x": 15, "y": 15, **example, "props": props}
        added = mcp.call(
            "add_block", sheet_id=sheet["id"], version=sheet["version"], page=1, **args
        )
        assert not added.get("isError"), added
        image = mcp.call("render_preview", sheet_id=sheet["id"])
        assert not image.get("isError"), image
        assert image["content"][0]["type"] == "image"
    finally:
        mcp.stop()
