#!/usr/bin/env python3
"""Drive Blattomat the way a teacher does, and keep the proof.

Run from the repo root:

    uv run python .cursor/skills/verify-blattwerk/drive.py prove

`prove` launches an isolated server, checks it, drives the editor and the
clipboard, runs two WebKit node ids, tears the server down, and checks that
the proof files are still there. The other commands are the same steps apart.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import Locator, Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[3]
HOME = Path("/tmp/blattwerk-verify")
CURRENT = HOME / "current.json"
PASSWORD = "verify-blatt"
WORDS = "Hallo"
MEASURED = """() => {
    const desk = document.querySelector('.desk'), look = getComputedStyle(desk);
    const room = desk.clientWidth - parseFloat(look.paddingLeft) - parseFloat(look.paddingRight);
    const sheets = [...desk.querySelectorAll('.sheet')];
    const widest = Math.max(...sheets.map((el) => el.getBoundingClientRect().width));
    return Math.abs(widest - room) < 1;
}"""
EDITOR_NODE = "tests/test_keys.py::test_enter_and_f2_open_a_text_with_all_of_it_picked"
CLIP_NODE = "tests/test_clipboard.py::test_the_button_ausschneiden_cuts"
USAGE = """\
usage:
  drive.py launch
  drive.py doctor
  drive.py drive editor|clipboard
  drive.py webkit <pytest-node-id>...
  drive.py cleanup
  drive.py prove
"""


def say(text: str) -> None:
    print(f"verify: {text}", flush=True)


def read_run() -> dict:
    if not CURRENT.is_file():
        raise SystemExit("no verification server is recorded; run launch")
    return json.loads(CURRENT.read_text())


def write_run(run: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    CURRENT.write_text(json.dumps(run, indent=2) + "\n")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\0", b" ").decode()


def environ(pid: int) -> dict[str, str]:
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes()
    except OSError:
        return {}
    found = {}
    for item in raw.split(b"\0"):
        if b"=" in item:
            key, value = item.split(b"=", 1)
            found[key.decode()] = value.decode()
    return found


def http_status(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except OSError:
        return 0


def launch() -> dict:
    if CURRENT.is_file():
        old = json.loads(CURRENT.read_text())
        if alive(old["pid"]):
            raise SystemExit(
                f"a server is already up (pid {old['pid']}, {old['origin']}); run cleanup first"
            )
    run_id = time.strftime("%Y%m%d%H%M%S")
    data = HOME / "data" / run_id
    evidence = HOME / "evidence" / run_id
    data.mkdir(parents=True)
    evidence.mkdir(parents=True)
    port = free_port()
    log_path = evidence / "server.log"
    log = log_path.open("ab")
    env = os.environ.copy()
    env["BLATTWERK_DATA_DIR"] = str(data)
    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "blattwerk.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log.close()
    run = {
        "run_id": run_id,
        "pid": proc.pid,
        "port": port,
        "origin": f"http://localhost:{port}",
        "data_dir": str(data),
        "evidence_dir": str(evidence),
        "log": str(log_path),
    }
    write_run(run)
    deadline = time.time() + 30
    status = 0
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SystemExit(f"server exited {proc.returncode}; see {log_path}")
        status = http_status(f"http://127.0.0.1:{port}/api/me")
        if status == 401:
            say(f"launch pid={proc.pid} origin={run['origin']} data={data}")
            return run
        time.sleep(0.1)
    raise SystemExit(f"server never returned 401 from /api/me (last status {status})")


def doctor() -> dict:
    run = read_run()
    problems = []
    pid = run["pid"]
    if not alive(pid):
        problems.append(f"pid {pid} is not running")
    command = cmdline(pid)
    if "blattwerk.app:app" not in command or f"--port {run['port']}" not in command:
        problems.append(f"pid {pid} is not this server: {command!r}")
    data = environ(pid).get("BLATTWERK_DATA_DIR")
    if data != run["data_dir"]:
        problems.append(f"data dir is {data!r}, expected {run['data_dir']}")
    if not str(run["data_dir"]).startswith(str(HOME / "data") + os.sep):
        problems.append(f"data dir is outside {HOME / 'data'}")
    status = http_status(f"http://127.0.0.1:{run['port']}/api/me")
    if status != 401:
        problems.append(f"/api/me returned {status}, expected 401")
    index = ROOT / "src/blattwerk/static/index.html"
    if not index.is_file():
        problems.append("built frontend is missing; run mise run build")
    text = "\n".join(problems) if problems else "ok"
    out = Path(run["evidence_dir"]) / "doctor.txt"
    out.write_text(
        "\n".join(
            [
                f"origin {run['origin']}",
                f"pid {pid}",
                f"data {run['data_dir']}",
                f"static {index}",
                f"/api/me {status}",
                text,
                "",
            ]
        )
    )
    if problems:
        raise SystemExit("doctor: " + "; ".join(problems))
    say(f"doctor ok {run['origin']} pid={pid}")
    return run


def invite(run: dict) -> str:
    env = os.environ.copy()
    env["BLATTWERK_DATA_DIR"] = run["data_dir"]
    path = subprocess.check_output(
        ["uv", "run", "python", "-m", "blattwerk", "invite", "--admin"],
        cwd=ROOT,
        env=env,
        text=True,
    ).strip()
    if not path.startswith("/einladung/"):
        raise SystemExit(f"invite printed {path!r}")
    return path


def settle(page: Page) -> None:
    expect(page.locator('main.editor[data-ready="1"]')).to_be_visible(timeout=15000)
    page.evaluate("document.fonts.ready.then(() => 0)")
    page.wait_for_function(MEASURED, timeout=15000)


def dismiss_tour(page: Page) -> str:
    tour = page.locator("section.tour")
    try:
        tour.wait_for(state="visible", timeout=3000)
    except Exception:
        return "no tour"
    tour.get_by_role("button", name="Beenden").click()
    expect(tour).to_be_hidden()
    return "Beenden"


def header_tool(page: Page, label: str) -> tuple[Locator, str]:
    page.evaluate("document.fonts.ready.then(() => 0)")
    top = page.locator("header .top")
    button = top.get_by_label(label, exact=True)
    if button.count():
        return button, "bar"
    top.get_by_label("Mehr", exact=True).click()
    return page.locator("dialog.menu").get_by_label(label, exact=True), "Mehr"


def saved(page: Page) -> None:
    status = page.locator("header [role=status]")
    expect(status).to_have_text(re.compile(r"^Speichert"), timeout=5000)
    expect(status).to_have_text("Gespeichert", timeout=8000)


def texts(page: Page) -> list[str]:
    return [line.strip() for line in page.locator(".block[data-id]").all_inner_texts()]


def reopen(page: Page) -> None:
    page.reload(wait_until="domcontentloaded")
    settle(page)


def sheet_body(page: Page, origin: str) -> dict:
    sheet_id = page.url.rstrip("/").rsplit("/", 1)[1]
    response = page.request.get(f"{origin}/api/sheets/{sheet_id}")
    if response.status != 200:
        raise RuntimeError(f"GET /api/sheets/{sheet_id} returned {response.status}")
    return response.json()


def open_editor(page: Page, run: dict, email: str) -> str:
    path = invite(run)
    page.goto(run["origin"] + path)
    expect(page.get_by_role("heading", name="Willkommen bei Blattomat")).to_be_visible()
    page.get_by_label("E-Mail").fill(email)
    page.get_by_label("Passwort").fill(PASSWORD)
    page.get_by_role("button", name="Konto anlegen").click()
    expect(page.get_by_role("heading", name="Meine Blätter")).to_be_visible(timeout=10000)
    page.get_by_role("button", name="Neues Blatt").click()
    settle(page)
    tour = dismiss_tour(page)
    expect(page.get_by_label("Titel")).to_have_value("Unbenanntes Blatt")
    page.evaluate("navigator.clipboard.writeText('')")
    return tour


def type_hallo(page: Page) -> None:
    bar = page.locator('[role="toolbar"][aria-label="Einfügen"]')
    bar.get_by_role("button", name="Text", exact=True).click()
    field = page.locator(".block.sel .ProseMirror")
    expect(field).to_be_focused(timeout=5000)
    page.keyboard.type(WORDS)
    expect(field).to_have_text(WORDS)
    page.keyboard.press("F2")
    expect(page.locator(".ProseMirror")).to_have_count(0)
    expect(page.locator(".block.sel")).to_have_count(1)


def snap(page: Page, folder: Path, name: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(folder / f"{name}.png"))
    aria = page.locator("main.editor").aria_snapshot()
    (folder / f"{name}.aria.txt").write_text(aria)


@contextmanager
def browser(run: dict, folder: Path, email: str) -> Generator[tuple[Page, str]]:
    playwright = sync_playwright().start()
    chrome = playwright.chromium.launch(headless=True)
    context = chrome.new_context(viewport={"width": 1400, "height": 1000})
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    page = context.new_page()
    try:
        tour = open_editor(page, run, email)
        yield page, tour
    except Exception:
        folder.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(folder / "failure.png"))
        raise
    finally:
        context.close()
        chrome.close()
        playwright.stop()


def drive(feature: str) -> None:
    if feature not in ("editor", "clipboard"):
        raise SystemExit(USAGE)
    run = doctor()
    folder = Path(run["evidence_dir"]) / feature
    email = f"verify-{run['run_id']}-{feature}@example.com"
    lines = [f"feature {feature}", f"email {email}"]
    with browser(run, folder, email) as (page, tour):
        lines.append(f"tour {tour}")
        type_hallo(page)
        lines.append("typed Hallo and left the field with F2")
        if feature == "clipboard":
            copy_button, copy_where = header_tool(page, "Kopieren")
            expect(copy_button).to_be_enabled()
            copy_button.click()
            paste_button, paste_where = header_tool(page, "Einfügen")
            paste_button.click()
            expect(page.locator(".block[data-id]")).to_have_count(2)
            lines.append(f"Kopieren via {copy_where}; Einfügen via {paste_where}; two blocks")
            page.keyboard.press("Control+c")
            page.keyboard.press("Control+v")
            expect(page.locator(".block[data-id]")).to_have_count(3)
            lines.append("Control+c then Control+v; three blocks")
        saved(page)
        lines.append("header status Gespeichert")
        snap(page, folder, "before-reload")
        want = 1 if feature == "editor" else 3
        reopen(page)
        found = texts(page)
        if found != [WORDS] * want:
            raise RuntimeError(f"after reload texts were {found!r}")
        lines.append(f"after reload {found}")
        body = sheet_body(page, run["origin"])
        stored = [block["props"].get("text") for block in body["doc"]["pages"][0]["blocks"]]
        if stored != [WORDS] * want:
            raise RuntimeError(f"stored texts were {stored!r}")
        (folder / "sheet.json").write_text(json.dumps(body, indent=2) + "\n")
        lines.append(f"GET /api/sheets stored {stored}")
        snap(page, folder, "after-reload")
    (folder / "result.txt").write_text("\n".join(lines) + "\n")
    say(f"drive {feature} " + "; ".join(lines))


def webkit(node_ids: list[str]) -> None:
    if not node_ids:
        raise SystemExit(USAGE)
    run = read_run() if CURRENT.is_file() else None
    evidence = Path(run["evidence_dir"]) if run else HOME / "evidence" / "webkit-only"
    evidence.mkdir(parents=True, exist_ok=True)
    log_path = evidence / ("webkit-" + node_ids[0].rsplit("::", 1)[-1][:40] + ".log")
    if len(node_ids) > 1:
        log_path = evidence / "webkit.log"
    command = ["mise", "run", "test:webkit", "--", "-n", "0", "--tb=short", *node_ids]
    say("webkit " + " ".join(command))
    with log_path.open("w") as log:
        log.write("$ " + " ".join(command) + "\n")
        log.flush()
        completed = subprocess.run(
            command,
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=480,
            check=False,
        )
    text = log_path.read_text()
    tail = "\n".join(text.splitlines()[-30:])
    print(tail, flush=True)
    if completed.returncode != 0:
        raise SystemExit(f"webkit exited {completed.returncode}; see {log_path}")
    say(f"webkit passed; log {log_path}")


def cleanup() -> None:
    if not CURRENT.is_file():
        say("cleanup nothing to stop")
        return
    run = json.loads(CURRENT.read_text())
    pid = run["pid"]
    evidence = run["evidence_dir"]
    if alive(pid):
        os.killpg(pid, 15)
        deadline = time.time() + 5
        while time.time() < deadline and alive(pid):
            time.sleep(0.1)
        if alive(pid):
            os.killpg(pid, 9)
    data = Path(run["data_dir"])
    if data.is_dir() and str(data).startswith(str(HOME / "data") + os.sep):
        subprocess.run(["rm", "-rf", str(data)], check=True)
    CURRENT.unlink(missing_ok=True)
    say(f"cleanup stopped pid {pid}; evidence kept at {evidence}")


def prove() -> None:
    run = launch()
    failed = None
    try:
        doctor()
        drive("editor")
        drive("clipboard")
        webkit([EDITOR_NODE, CLIP_NODE])
    except Exception as error:
        failed = error
    finally:
        cleanup()
    evidence = Path(run["evidence_dir"])
    needed = [
        evidence / "doctor.txt",
        evidence / "editor" / "after-reload.png",
        evidence / "editor" / "after-reload.aria.txt",
        evidence / "editor" / "sheet.json",
        evidence / "editor" / "result.txt",
        evidence / "clipboard" / "after-reload.png",
        evidence / "clipboard" / "after-reload.aria.txt",
        evidence / "clipboard" / "sheet.json",
        evidence / "clipboard" / "result.txt",
        evidence / "webkit.log",
    ]
    missing = [str(path) for path in needed if not path.is_file()]
    if alive(run["pid"]):
        missing.append(f"pid {run['pid']} still running")
    if Path(run["data_dir"]).exists():
        missing.append(f"data dir still there: {run['data_dir']}")
    summary = evidence / "summary.txt"
    lines = [f"run {run['run_id']}", f"origin was {run['origin']}"]
    if failed:
        lines.append(f"failed: {failed}")
    if missing:
        lines.append("missing after cleanup: " + ", ".join(missing))
    else:
        lines.append("evidence still present after cleanup")
    summary.write_text("\n".join(lines) + "\n")
    say("summary " + "; ".join(lines))
    if failed or missing:
        raise SystemExit(1)


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        raise SystemExit(USAGE)
    command = argv[1]
    if command == "launch":
        launch()
    elif command == "doctor":
        doctor()
    elif command == "drive":
        if len(argv) != 3:
            raise SystemExit(USAGE)
        drive(argv[2])
    elif command == "webkit":
        webkit(argv[2:])
    elif command == "cleanup":
        cleanup()
    elif command == "prove":
        prove()
    else:
        raise SystemExit(USAGE)


if __name__ == "__main__":
    main(sys.argv)
