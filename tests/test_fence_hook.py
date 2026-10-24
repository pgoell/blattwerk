"""The fence hook (.claude/hooks/fence.py) keeps build sessions off live data, docker and forced
pushes. Each test feeds it one tool call on stdin, the way Claude Code does, and reads the verdict.

No command here ever runs: the strings only reach the hook, and HOME points at a tmp folder.
`@HOME@` in a command stands for that folder, spelled out.
"""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude/hooks/fence.py"
SETTINGS = REPO / ".claude/settings.json"
LIVE = "~/.local/share/blattwerk"
BACKUPS = "~/.local/share/blattwerk-backups"
ABS = "@HOME@/.local/share/blattwerk"
CANARY = "~/.local/share/blattwerk-canary"
TOOLS = ("Bash", "Write", "Edit", "NotebookEdit")


@pytest.fixture(scope="module")
def home(tmp_path_factory):
    """A fake HOME with the live folder, its canary copy, the backups folder and a link to the
    live folder."""
    home = tmp_path_factory.mktemp("home")
    share = home / ".local/share"
    (share / "blattwerk").mkdir(parents=True)
    (share / "blattwerk-canary").mkdir()
    (share / "blattwerk-backups").mkdir()
    (home / "repo").mkdir()
    (home / "link").symlink_to(share / "blattwerk")
    return home


def run(command, *, home, cwd=None, tool="Bash", key="command", stdin=None, argv=None):
    """Hand the hook one tool call, or the raw text `stdin`."""
    call = {"tool_name": tool, "tool_input": {key: command}, "cwd": str(cwd or REPO)}
    env = {**os.environ, "HOME": str(home), "CLAUDE_PROJECT_DIR": str(REPO)}
    env.pop("XDG_DATA_HOME", None)
    return subprocess.run(
        argv or ["python3", str(HOOK)],
        input=json.dumps(call) if stdin is None else stdin,
        text=True,
        capture_output=True,
        env=env,
        timeout=30,
    )


def refused(done, *words):
    """The call was refused in the agreed shape, and the text names each of `words`."""
    lines = [line for line in done.stderr.splitlines() if line.strip()]
    assert done.returncode == 2, f"exit {done.returncode}: {done.stderr}"
    assert done.stderr.startswith("Refused by the fence"), done.stderr
    assert lines[-1].startswith("BLOCKED"), done.stderr
    for word in words:
        assert word.lower() in done.stderr.lower(), done.stderr


def allowed(done):
    assert done.returncode == 0, f"exit {done.returncode}: {done.stderr}"


def cases(refuse=(), allow=()):
    """Parametrize over commands. A command is a string, or (string, "live" | "canary" |
    "backups") where the tool call comes from that folder."""
    rows = [(c, True) for c in refuse] + [(c, False) for c in allow]
    params = []
    for case, refuse_it in rows:
        command, cwd = (case, None) if isinstance(case, str) else case
        name = f"{'refuse' if refuse_it else 'allow'}: {command}" + (f" (in {cwd})" if cwd else "")
        params.append(pytest.param(command, cwd, refuse_it, id=name))
    return pytest.mark.parametrize(("command", "cwd", "refuse"), params)


def check(home, command, cwd, refuse):
    share = home / ".local/share"
    names = {"live": "blattwerk", "canary": "blattwerk-canary", "backups": "blattwerk-backups"}
    folder = share / names[cwd] if cwd else None
    done = run(command.replace("@HOME@", str(home)), home=home, cwd=folder)
    assert "hook crashed" not in done.stderr, done.stderr
    refused(done) if refuse else allowed(done)


def test_a1_settings_register_the_hook(home):
    entries = json.loads(SETTINGS.read_text()).get("hooks", {}).get("PreToolUse", [])
    fences = [
        (entry.get("matcher") or "*", hook["command"])
        for entry in entries
        for hook in entry.get("hooks", [])
        if "fence.py" in hook.get("command", "")
    ]
    assert fences, "settings.json has no PreToolUse hook that runs fence.py"
    for tool in TOOLS:
        assert any(m == "*" or re.fullmatch(m, tool) for m, _ in fences), f"{tool} is not covered"
    command = next(c for m, c in fences if m == "*" or re.fullmatch(m, "Bash"))
    argv = ["bash", "-c", command]
    refused(run("gh pr merge 5 --admin", home=home, argv=argv), "--admin")
    allowed(run("mise tasks", home=home, argv=argv))
    # A checkout of a commit from before the hook must not lock the session out: python3 on a
    # missing file exits 2, which Claude Code reads as a refusal.
    gone = subprocess.run(
        argv,
        input="{}",
        text=True,
        capture_output=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(home)},
    )
    assert gone.returncode == 0, gone.stderr


@cases(refuse=["gh pr merge 5 --admin", "gh pr merge --squash --admin 5"])
def test_a2_refuses_admin(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


@cases(
    refuse=[
        "git commit --no-verify -m x",
        "git push --no-verify",
        "git push --no-verify origin feat/x",
    ],
    allow=["git grep -n -- '--no-verify' .claude tests", "git grep -e --no-verify"],
)
def test_a3_refuses_no_verify(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


@cases(
    refuse=[
        "git push --force",
        "git push --force origin feat/x",
        "git push origin feat/x --force",
    ]
)
def test_a4_refuses_force_push(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


@cases(
    refuse=[
        "mise run repo:apply-settings",
        "mise repo:apply-settings",
        "bash scripts/apply-github-settings.sh",
    ],
    allow=["mise run repo:check-settings", "bash scripts/apply-github-settings.sh --check"],
)
def test_a5_refuses_apply_settings(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


VERBS = ("up", "down", "rm", "stop", "kill")


@cases(
    refuse=dict.fromkeys(
        [
            *(f"{tool} {verb}" for tool in ("docker compose", "docker-compose") for verb in VERBS),
            *(f"docker {verb} x" for verb in VERBS[2:]),
            "docker system prune -f",
            "docker volume rm x",
            "docker volume ls",
            "docker system df",
            "docker compose up -d",
            "docker compose -f a.yml down",
            "docker-compose down -v",
            "docker container rm x",
            "docker container stop x",
            "docker stop blattwerk",
            "docker rm -f x",
            "docker compose --progress plain up -d",
            "docker compose --ansi never down",
            "docker compose --progress=plain up -d",
            "docker restart blattwerk",
            "docker compose restart",
            "docker container restart x",
            "docker rmi blattwerk:prev",
            "docker image remove blattwerk-blattwerk:prev",
            "docker container remove -f blattwerk",
            "docker image prune -f",
            "docker container prune",
            "docker builder prune -af",
            "docker buildx prune",
            "docker network prune",
            "sudo docker restart blattwerk",
        ]
    )
)
def test_a6_refuses_docker(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


@cases(
    refuse=[
        f"rm {LIVE}/blattwerk.db",
        f"rm -rf {LIVE}/users",
        f"mv {LIVE}/blattwerk.db /tmp/x",
        f"mv /tmp/x {LIVE}/blattwerk.db",
        f"echo x > {LIVE}/note",
        f"echo x >> {LIVE}/note",
        f"cmd &> {LIVE}/log",
        f'sqlite3 {LIVE}/blattwerk.db "delete from users"',
        f"sqlite3 {LIVE}/blattwerk.db .tables",
    ]
)
def test_a7_refuses_writes_to_live_data(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


@pytest.mark.parametrize(
    ("command", "word"),
    [
        ("gh pr merge 5 --admin", "--admin"),
        ("git commit --no-verify -m x", "--no-verify"),
        ("git push --force", "force"),
        ("mise run repo:apply-settings", "apply-settings"),
        ("docker compose down", "docker"),
        (f"rm {LIVE}/blattwerk.db", "live"),
    ],
    ids=["admin", "no-verify", "force", "apply-settings", "docker", "live"],
)
def test_a9_refusal_text(home, command, word):
    refused(run(command, home=home), word)


@cases(
    allow=[
        "git push -u origin feat/x",
        "git push",
        "git push origin feat/x",
        "git push -q -u origin feat/x",
        "git push origin --delete feat/x",
        "gh pr merge 227 --squash --auto --delete-branch",
        "gh run cancel 123",
        "gh run rerun 123",
        "gh pr checks 227 --watch --fail-fast",
        "mise run test",
        "mise run test:one -- tests/test_keys.py::test_name",
        "mise run test:flaky -- tests/test_keys.py::test_name",
        "mise run lint",
        "mise run build",
        "mise tasks",
        "mise run shot -- sheet.json out/",
        "uv run pytest -n 0 -x tests/test_keys.py",
        'sqlite3 "file:$HOME/.local/share/blattwerk/blattwerk.db?mode=ro" '
        '"select count(*) from users"',
        f"sqlite3 -readonly {LIVE}/blattwerk.db .tables",
        f"sqlite3 --readonly {LIVE}/blattwerk.db .tables",
        f"cp {LIVE}/blattwerk.db {BACKUPS}/blattwerk-2026-10-09-pr227.db",
        f"mkdir -p {BACKUPS}",
        f"ls -la {LIVE}",
        f"cat {LIVE}/blattwerk.db | sha256sum",
        f"du -sh {LIVE}",
        'git commit -m "feat: x"',
        "git commit --allow-empty -m x",
        "rm -rf node_modules",
        "rm tests/probe_x.py",
        "echo x > /tmp/a",
        "ls nothing 2>/dev/null",
        "mise run test 2>&1 | tail -5",
        "curl -fsS https://blattwerk.pgoell.com/",
        "git checkout master && git pull",
        "gh run list --workflow Deploy -L 1 --json headSha,conclusion",
    ]
)
def test_a10_allowed_commands(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


SPELLINGS = [
    (f"{LIVE}/x", None),
    ("$HOME/.local/share/blattwerk/x", None),
    ("${HOME}/.local/share/blattwerk/x", None),
    (f'"{ABS}/x"', None),
    ("blattwerk.db", "live"),
    ("../blattwerk/blattwerk.db", "backups"),
    (f"{BACKUPS}/../blattwerk/x", None),
    ("@HOME@/link/x", None),
]


READ_ONLY = (
    f"import sqlite3; c=sqlite3.connect('file:{ABS}/blattwerk.db?mode=ro', uri=True); "
    "print(c.execute('select count(*) from users').fetchone())"
)


CANARY_SCRIPT = "open('@HOME@/.local/share/blattwerk-canary/x', 'w')"


DATA_DIRS = [LIVE, CANARY, "$HOME/.local/share/blattwerk", f'"{ABS}"', f"{LIVE}/users"]
