"""What the daily feedback job asks the model, and the shape it accepts back.

The prompt itself stays in feedback_triage.py. The caller passes it in, so this module
does not import the script that imports it.
"""

import base64
import json
import re
import subprocess
from pathlib import Path

VERDICTS = ("bug", "wish", "question", "nothing")

PICTURE_TYPES = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

MAX_PICTURE = 3_500_000


class ModelHasTools(Exception):
    """The model came up with tools or servers. The whole run stops."""


def sort_files(folder: Path):
    """Voice notes, pictures the model may see, and pictures it may not (heic, too big)."""
    voice, pictures, to_see = [], [], []
    for path in sorted(p for p in folder.iterdir() if p.is_file()):
        if path.name.startswith("audio-"):
            voice.append(path)
        elif path.name.startswith(("photo-", "screenshot-")):
            media = PICTURE_TYPES.get(path.suffix)
            if media and path.stat().st_size <= MAX_PICTURE:
                pictures.append((path, media))
            else:
                to_see.append(path)
    return voice, pictures, to_see


def image_block(path: Path, media: str) -> dict:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}}


def build_prompt(art, seite, voice_count, text, issues, ai=False) -> str:
    # The page path without its numbers: the issue must not name a sheet.
    page = re.sub(r"[0-9]+", "N", seite) if seite else "unknown"
    lines = [
        f"Kind of send: {art}",
        *(["Sent by: an AI model working through the Blattomat MCP, not a teacher"] if ai else []),
        f"Sent from page: {page}",
        f"Voice notes attached that you cannot hear: {voice_count}",
        "",
        f"The {'AI' if ai else 'teacher'}'s text, between the markers:",
        "<<<",
        text or "(no text)",
        ">>>",
        "",
        "Open issues:",
        *(f"#{number} {title}" for number, title in sorted(issues.items())),
    ]
    return "\n".join(lines)


def ask(model: str, prompt: str, images: list[dict], system: str) -> object:
    """One model call with no tools, no servers and no user settings. Returns the parsed answer."""
    message = {
        "type": "user",
        "message": {"role": "user", "content": [{"type": "text", "text": prompt}, *images]},
    }
    command = [
        "claude", "-p", "--model", model,
        "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
        "--tools", "", "--strict-mcp-config", "--no-session-persistence",
        "--setting-sources", "", "--system-prompt", system,
    ]  # fmt: skip
    # claude tells the model the folder it stands in, and a home folder names its owner.
    done = subprocess.run(
        command, input=json.dumps(message) + "\n", capture_output=True, text=True, timeout=600,
        cwd="/",
    )  # fmt: skip
    events = []
    for line in done.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    inits = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    if any(e.get("tools") or e.get("mcp_servers") for e in inits):
        raise ModelHasTools()
    results = [e for e in events if e.get("type") == "result"]
    # Without the init line, nothing says what the model could reach: its answer is not used.
    if not inits or done.returncode or not results or results[-1].get("is_error"):
        raise RuntimeError("the model call failed")
    if not isinstance(results[-1].get("result"), str):
        raise RuntimeError("the model gave no answer")
    # The model may wrap the object in a code fence.
    text = results[-1]["result"]
    return json.loads(text[text.find("{") : text.rfind("}") + 1])


def checked(verdict) -> tuple[str, str, str, int | None]:
    """The verdict in the shape the brief allows, else ValueError. bool is not an issue number."""
    if not isinstance(verdict, dict) or verdict.get("verdict") not in VERDICTS:
        raise ValueError("the verdict is not one of the four kinds")
    title, body, issue = verdict.get("title"), verdict.get("body"), verdict.get("issue")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
        raise ValueError("the title is not 1 to 120 characters")
    if not isinstance(body, str) or not 1 <= len(body.strip()) <= 4000:
        raise ValueError("the body is not 1 to 4000 characters")
    if issue is not None and type(issue) is not int:
        raise ValueError("the issue is not a number or null")
    return verdict["verdict"], title.strip(), body.strip(), issue
