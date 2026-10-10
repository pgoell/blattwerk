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


@cases(
    allow=[
        'git commit -m "never use --no-verify or docker compose down"',
        f'gh issue create --title "docker compose down fails" --body "use --admin, rm {LIVE}/x"',
        "gh pr create --title x --body \"$(cat <<'EOF'\n"
        f'Never merge with --admin, never git push --force.\nrm {LIVE}/x\nEOF\n)"',
        'echo "git push --force"',
        'grep -rn -e "--no-verify" .',
        "# don't amend\ncat > /tmp/x.sh <<'EOF'\ndocker compose up -d\nEOF",
        "awk '{print $1}' f # isn't it\ncat <<EOF\ngit push --force\nEOF",
    ],
    refuse=[
        "mise run lint && git push --force",
        "true; docker compose down",
        "echo hi | docker compose up -d",
        "echo $(git push --force)",
        'bash -c "git push --force"',
        f"sh -c 'rm {LIVE}/blattwerk.db'",
        "sudo docker compose down",
        "env FOO=1 git push --force",
        "true || gh pr merge 5 --admin",
        "mise run lint\ngit push --force",
        "timeout 60 git push --force origin x",
        "timeout 30 git commit --no-verify -m x",
        "timeout 120 docker compose down",
        "timeout -k 5 60 docker compose down",
        f"timeout 5 rm {LIVE}/blattwerk.db",
        "sudo -n docker compose up -d",
        "stdbuf -oL docker compose up",
        "watch -n 5 docker compose down",
        f'python3 -c "print(1 << n)"\nrm -rf {LIVE}',
        f'git commit -m "fix: read cat <<EOF bodies"\nrm -rf {LIVE}',
    ],
)
def test_i1_quotes_are_data_and_chains_are_checked(home, command, cwd, refuse):
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


@cases(
    refuse=[
        *((f"rm {path}", cwd) for path, cwd in SPELLINGS),
        *((f"echo x > {path}", cwd) for path, cwd in SPELLINGS),
        f"cd {LIVE} && rm blattwerk.db",
        f"cd {LIVE} && echo x > note",
        "rm -rf ~/.local/share",
        "rm -rf ~/.local",
        f"mv {LIVE} /tmp/gone",
        f"(cd {LIVE} && rm blattwerk.db)",
    ],
    allow=[
        f"(cd {LIVE} && ls -la) > listing.txt",
        f"(cd {LIVE} && sqlite3 -readonly blattwerk.db .tables); echo done > out.txt",
        f"pushd {LIVE} && ls && popd && echo x > notes.txt",
        f"rm {BACKUPS}/old.db",
        f"echo x > {BACKUPS}/note",
        ("rm blattwerk.db", "backups"),
        "rm -rf ~/.local/share/other",
    ],
)
def test_i2_spellings_of_the_live_folder(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


@cases(
    refuse=[
        "git commit -n -m x",
        "git commit -nm x",
        "git commit -an -m x",
        "git push -f",
        "git push -uf origin x",
        "git push --force-with-lease",
        "git push --force-with-lease=x:y origin x",
        "git push --force-if-includes",
        "git push origin +main",
        "git push origin +HEAD:main",
        "git push --mirror",
        "git -C /tmp/r push --force",
        "git -c a.b=c push -f",
    ],
    allow=["git push -n origin x", 'git commit -m "-n"', "git commit -am x"],
)
def test_i3_short_and_other_git_flags(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


@cases(
    refuse=[
        f"cp /tmp/x {LIVE}/blattwerk.db",
        f"cp -r /tmp/u {LIVE}/",
        f"cp -t {LIVE} /tmp/x",
        f"rsync -a /tmp/u/ {LIVE}/users/",
        f"echo x | tee {LIVE}/note",
        f"dd if=/dev/zero of={LIVE}/blattwerk.db",
        f"truncate -s 0 {LIVE}/blattwerk.db",
        f"touch {LIVE}/x",
        f"mkdir {LIVE}/new",
        f"rmdir {LIVE}/users",
        f"chmod 600 {LIVE}/blattwerk.db",
        f"chown root {LIVE}/blattwerk.db",
        f"ln -s /tmp/x {LIVE}/l",
        f"sed -i s/a/b/ {LIVE}/users/1/x.json",
        f"cp {LIVE}/blattwerk.db{{,.bak}}",
        f"cp {LIVE}/blattwerk.db{{.bak,}}",
        f"cd {LIVE} && cp blattwerk.db{{,.bak}}",
    ],
    allow=[
        f"cp -r {LIVE}/users /tmp/copy",
        f"rsync -a {LIVE}/ /tmp/copy/",
        f"cp {LIVE}/blattwerk.db{{,-wal,-shm}} /tmp/copy/",
        f"rsync -a {LIVE}/{{a,b}} /tmp/copy/",
        f"sed -n 1p {LIVE}/users/1/x.json",
    ],
)
def test_i4_other_writers(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


READ_ONLY = (
    f"import sqlite3; c=sqlite3.connect('file:{ABS}/blattwerk.db?mode=ro', uri=True); "
    "print(c.execute('select count(*) from users').fetchone())"
)


@cases(
    refuse=[
        f"python -c \"import sqlite3; sqlite3.connect('{ABS}/blattwerk.db')\"",
        f"uv run python -c \"open('{ABS}/x','w')\"",
        f"python3 - <<'EOF'\nimport os\nos.remove(os.path.expanduser('{LIVE}/blattwerk.db'))\nEOF",
        f"node -e \"require('fs').rmSync('{ABS}/x')\"",
        f"bash <<'EOF'\nrm {LIVE}/x\nEOF",
        f"# don't write\npython3 - <<'EOF'\nopen('{ABS}/x', 'w')\nEOF",
    ],
    allow=[
        f'python3 -c "{READ_ONLY}"',
        "uv run python - <<'EOF'\n" + READ_ONLY.replace("; ", "\n") + "\nEOF",
        'python3 -c "print(1)"',
        f"python3 -c \"open('{ABS}-backups/x','w')\"",
    ],
)
def test_i5_inline_scripts(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


@cases(
    allow=[
        "docker ps",
        "docker ps -a",
        "docker logs blattwerk",
        "docker logs -f --tail 50 blattwerk",
        "docker inspect blattwerk",
        "docker images",
        "docker compose ps",
        "docker compose logs --tail 20",
        "docker run --rm img cmd",
        "docker exec blattwerk ls",
        "docker build -t x .",
        "docker tag a b",
        "docker image inspect x",
        "docker image ls",
        "docker exec x restart",
        "mise run test:webkit",
        "mise run test:webkit -- -n 0 -x tests/test_keys.py::test_name",
    ]
)
def test_i6_harmless_docker(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


@pytest.mark.parametrize(
    ("tool", "key", "path", "refuse"),
    [
        *((tool, "file_path", f"{ABS}/users/1/x.json", True) for tool in ("Write", "Edit")),
        ("NotebookEdit", "notebook_path", f"{ABS}/x.ipynb", True),
        *((tool, "file_path", "@HOME@/repo/x.py", False) for tool in ("Write", "Edit")),
        ("NotebookEdit", "notebook_path", "@HOME@/repo/x.ipynb", False),
        *((tool, "file_path", f"{ABS}-backups/x.db", False) for tool in ("Write", "Edit")),
        ("NotebookEdit", "notebook_path", f"{ABS}-backups/x.ipynb", False),
        ("Read", "file_path", f"{ABS}/blattwerk.db", False),
    ],
    ids=lambda value: value if isinstance(value, str) else ("allow", "refuse")[value],
)
def test_i7_file_tools(home, tool, key, path, refuse):
    done = run(path.replace("@HOME@", str(home)), home=home, tool=tool, key=key)
    refused(done, "live") if refuse else allowed(done)


@cases(
    refuse=['echo "unbalanced && git push --force', f'rm {LIVE}/x "oops'],
    allow=['echo "unbalanced'],
)
def test_i8_unparsable_command(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


CANARY_SCRIPT = "open('@HOME@/.local/share/blattwerk-canary/x', 'w')"


@cases(
    refuse=[
        f"rm {CANARY}/blattwerk.db",
        f"rm -rf {CANARY}",
        f"mv {CANARY}/blattwerk.db /tmp/x",
        f"chmod 600 {CANARY}/blattwerk.db",
        f"touch {CANARY}/x",
        f"cp /tmp/x {CANARY}/blattwerk.db",
        f"sed -i s/a/b/ {CANARY}/users/1/x.json",
        f"echo x | tee {CANARY}/note",
        f"dd if=/dev/zero of={CANARY}/blattwerk.db",
        f"echo x > {CANARY}/note",
        f"echo x >> {CANARY}/note",
        "echo x > $HOME/.local/share/blattwerk-canary/note",
        ("rm blattwerk.db", "canary"),
        ("echo x > note", "canary"),
        f"cd {CANARY} && rm blattwerk.db",
        f"sqlite3 {CANARY}/blattwerk.db .tables",
        f'sqlite3 {CANARY}/blattwerk.db "delete from users"',
        f'python3 -c "{CANARY_SCRIPT}"',
        f"python3 - <<'EOF'\n{CANARY_SCRIPT}\nEOF",
        f"bash <<'EOF'\nrm {CANARY}/x\nEOF",
        f"sh -c 'rm {CANARY}/x'",
        f"sqlite3 <<'EOF'\n.open {CANARY}/blattwerk.db\nEOF",
    ],
    allow=[
        f"ls -la {CANARY}",
        f"cat {CANARY}/blattwerk.db | sha256sum",
        f"cp {CANARY}/blattwerk.db /tmp/copy.db",
        f"cp -r {CANARY} {BACKUPS}/canary",
        f"sqlite3 -readonly {CANARY}/blattwerk.db .tables",
        f"rm {BACKUPS}/old.db",
        f"echo x > {BACKUPS}/note",
        f"touch {BACKUPS}/x",
        f"python3 -c \"open('{ABS}-backups/x','w')\"",
        f"python3 -c \"open('{ABS}-canary-old/x','w')\"",
        "rm -rf ~/.local/share/blattwerk-canary-old",
    ],
)
def test_canary_copy_is_fenced(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


@pytest.mark.parametrize(
    ("tool", "key", "path", "refuse"),
    [
        *((tool, "file_path", f"{ABS}-canary/users/1/x.json", True) for tool in ("Write", "Edit")),
        ("NotebookEdit", "notebook_path", f"{ABS}-canary/x.ipynb", True),
        ("Read", "file_path", f"{ABS}-canary/blattwerk.db", False),
    ],
    ids=lambda value: value if isinstance(value, str) else ("allow", "refuse")[value],
)
def test_canary_copy_file_tools(home, tool, key, path, refuse):
    done = run(path.replace("@HOME@", str(home)), home=home, tool=tool, key=key)
    refused(done, "canary copy") if refuse else allowed(done)


@pytest.mark.parametrize(
    ("command", "folder", "other"),
    [
        (f"rm {CANARY}/x", "canary copy", "live folder"),
        (f"echo x > {CANARY}/x", "canary copy", "live folder"),
        (f'python3 -c "{CANARY_SCRIPT}"', "canary copy", "live folder"),
        (f"rm {LIVE}/x", "live folder", "canary"),
        (f"python3 -c \"open('{ABS}/x', 'w')\"", "live folder", "canary"),
    ],
    ids=["rm canary", "redirect canary", "script canary", "rm live", "script live"],
)
def test_refusal_names_the_folder_hit(home, command, folder, other):
    done = run(command.replace("@HOME@", str(home)), home=home)
    refused(done, folder)
    assert other not in done.stderr, done.stderr
    assert "hook crashed" not in done.stderr


def test_parent_of_the_canary_copy(home, tmp_path):
    """With the live folder gone, the canary copy alone still fences its parents."""
    share = tmp_path / ".local/share"
    (share / "blattwerk-canary").mkdir(parents=True)
    for command in ("rm -rf ~/.local/share", "rm -rf ~/.local", f"mv {CANARY} /tmp/gone"):
        done = run(command, home=tmp_path)
        refused(done)
        assert "hook crashed" not in done.stderr
    assert "canary copy" in run(f"mv {CANARY} /tmp/gone", home=tmp_path).stderr
    allowed(run("rm -rf ~/.local/share/other", home=tmp_path))


@cases(
    refuse=[
        f"find {LIVE} -name '*.json' -delete",
        f"find {CANARY} -delete",
        f"find {LIVE}/users -type f -exec rm {{}} +",
        f"find {LIVE} -exec rm {{}} \\;",
        f"find {LIVE} -execdir rm {{}} +",
        f"find {LIVE} -ok rm {{}} \\;",
        f"find {LIVE} -okdir rm {{}} \\;",
        f"find -L {LIVE} -delete",
        f"find /tmp {LIVE} -delete",
        "find ~/.local/share -name '*.db' -delete",
        ("find -delete", "live"),
        ("find . -delete", "canary"),
        ("find -name x -delete", "live"),
        f"cd {LIVE} && find -type f -delete",
        f"sudo find {LIVE} -delete",
        f"find {LIVE} \\( -name a -o -name b \\) -delete",
        f"find -- {LIVE} -delete",
        f"find -D tree {CANARY} -delete",
        "find ~ -name x -exec rm {} +",
    ],
    allow=[
        f"find {LIVE} -name x",
        f"find {LIVE} -type f -newer /tmp/x",
        f"find {CANARY}",
        ("find", "live"),
        "find . -name '*.pyc' -delete",
        "find /tmp/x -exec rm {} +",
        "find ~ -name x -exec grep foo {} +",
        "cd ~/.local/share && find . -name x -exec ls {} \\;",
        "find . \\( -name a -o -name b \\) -print",
        "echo \\( x \\)",
        f"find {BACKUPS} -mtime +30 -delete",
        "find -delete",
        "find",
        "find -L",
        "find -exec",
    ],
)
def test_find_that_deletes_or_runs(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


DATA_DIRS = [LIVE, CANARY, "$HOME/.local/share/blattwerk", f'"{ABS}"', f"{LIVE}/users"]


@cases(
    refuse=[
        *(f"BLATTWERK_DATA_DIR={folder} mise run dev:api" for folder in DATA_DIRS),
        f"BLATTWERK_DATA_DIR={LIVE}",
        f"export BLATTWERK_DATA_DIR={LIVE}",
        f"export BLATTWERK_DATA_DIR={CANARY}",
        f"export FOO=1 BLATTWERK_DATA_DIR={LIVE}",
        f"declare -x BLATTWERK_DATA_DIR={LIVE}",
        f"env BLATTWERK_DATA_DIR={LIVE} uv run uvicorn blattwerk.app:app",
        f"env -u FOO BLATTWERK_DATA_DIR={LIVE} mise run dev:api",
        f"sudo BLATTWERK_DATA_DIR={LIVE} mise run dev:api",
        f"timeout 5 env BLATTWERK_DATA_DIR={LIVE} mise run dev:api",
        f"FOO=1 BLATTWERK_DATA_DIR={LIVE} mise run dev:api",
        f"true && BLATTWERK_DATA_DIR={LIVE} mise run dev:api",
        ("BLATTWERK_DATA_DIR=. mise run dev:api", "live"),
        ("BLATTWERK_DATA_DIR=../blattwerk-canary mise run dev:api", "backups"),
    ],
    allow=[
        "BLATTWERK_DATA_DIR=/tmp/data mise run dev:api",
        f"BLATTWERK_DATA_DIR={BACKUPS}/copy mise run dev:api",
        f"export BLATTWERK_DATA_DIR={BACKUPS}",
        "export BLATTWERK_DATA_DIR=$(mktemp -d)",
        f"OTHER_DIR={LIVE} mise run dev:api",
        f'echo "BLATTWERK_DATA_DIR={LIVE}"',
        "BLATTWERK_DATA_DIR= mise run dev:api",
        ("BLATTWERK_DATA_DIR= mise run dev:api", "live"),
        "export",
        "export BLATTWERK_DATA_DIR",
        "env",
    ],
)
def test_data_dir_variable(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


@cases(
    refuse=[
        f"docker run -v {LIVE}:/data img",
        f"docker run --rm -v {CANARY}:/data img cmd",
        f"docker run --volume {LIVE}:/data img",
        f"docker run --volume={LIVE}:/data img",
        f"docker run -v{ABS}:/data img",
        f"docker run -v {LIVE}/users:/data:rw img",
        f"docker run -v {LIVE}:/data:z img",
        "docker run -v ~/.local/share:/share img",
        f"docker run --mount type=bind,source={ABS},target=/data img",
        f"docker run --mount type=bind,src={ABS}-canary,dst=/data img",
        f"docker run --mount=type=bind,source={ABS}/users,target=/data img",
        f"docker run --mount type=bind,source={ABS},target=/data,readonly=false img",
        f"docker create -v {LIVE}:/data img",
        f"docker container run -v {LIVE}:/data img",
        f"docker compose run -v {LIVE}:/data web",
        ("docker run -v .:/data img", "live"),
    ],
    allow=[
        f"docker run -v {LIVE}:/data:ro img",
        f"docker run -v {LIVE}:/data:ro,z img",
        f"docker run --volume={CANARY}:/data:ro img",
        f"docker run --mount type=bind,source={ABS},target=/data,readonly img",
        f"docker run --mount type=bind,src={ABS},dst=/data,ro img",
        "docker run -v /tmp/data:/data img",
        f"docker run -v {BACKUPS}:/data img",
        "docker run --mount type=bind,source=/tmp/data,target=/data img",
        "docker run -v data:/data img",
        ("docker run -v data:/data img", "live"),
        "docker run -v /data img",
        "docker run",
        "docker run -v",
        "docker run --mount",
        "docker run --volume=",
        "docker run --mount=",
        "docker run --mount ,,=,",
        "docker run -v :",
        "docker create",
        "docker",
    ],
)
def test_docker_mounts(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


@cases(
    allow=[
        "",
        " ",
        ";",
        "find",
        "find (",
        "find !",
        "export",
        "declare -x",
        "env",
        "sudo",
        "timeout",
        "docker run -v",
        "docker run -v '",
        'export BLATTWERK_DATA_DIR="',
        "BLATTWERK_DATA_DIR=",
        "find -exec '",
        "git status",
        f"ls {LIVE}",
        "mise run test",
        f"sqlite3 -readonly {LIVE}/blattwerk.db .tables",
    ],
    refuse=[
        f'find {LIVE} -delete "oops',
        f'BLATTWERK_DATA_DIR={LIVE} cmd "oops',
        f'docker run -v {LIVE}:/data img "oops',
    ],
)
def test_odd_input_never_crashes(home, command, cwd, refuse):
    check(home, command, cwd, refuse)


@pytest.mark.parametrize("stdin", ["not json", ""], ids=["not json", "empty"])
def test_i8_invalid_stdin(home, stdin):
    refused(run(None, home=home, stdin=stdin))
