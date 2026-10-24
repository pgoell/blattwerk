"""The fence's reading of quotes, flags, writers and scripts.

The hook helpers live in test_fence_hook.py."""

# The fixture is imported, and each test names it as an argument.
# ruff: noqa: F811

import pytest
from test_fence_hook import (
    ABS,
    BACKUPS,
    LIVE,
    READ_ONLY,
    SPELLINGS,
    allowed,
    cases,
    check,
    home,  # noqa: F401
    refused,
    run,
)


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


@pytest.mark.parametrize("stdin", ["not json", ""], ids=["not json", "empty"])
def test_i8_invalid_stdin(home, stdin):
    refused(run(None, home=home, stdin=stdin))
