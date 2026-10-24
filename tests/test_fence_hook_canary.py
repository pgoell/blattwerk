"""The canary copy, find, the data dir, docker mounts, and the stage tasks.

The hook helpers live in test_fence_hook.py."""

# The fixture is imported, and each test names it as an argument.
# ruff: noqa: F811

import pytest
from test_fence_hook import (
    ABS,
    BACKUPS,
    CANARY,
    CANARY_SCRIPT,
    DATA_DIRS,
    LIVE,
    allowed,
    cases,
    check,
    home,  # noqa: F401
    refused,
    run,
)


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


# The stage goes up and down through its task alone: the task guards its one copy folder, and a
# docker call by hand could as well name the live container.


@cases(
    allow=["mise run stage:up", "mise run stage:down", "bash scripts/stage.sh up"],
    refuse=[
        "docker rm -f blattwerk-stage",
        "docker stop blattwerk-stage",
        "docker rm -f blattwerk",
        "docker stop blattwerk",
        "docker compose up -d",
        "docker compose down",
        "docker restart blattwerk",
    ],
)
def test_stage_a8_the_tasks_pass_and_docker_by_hand_does_not(home, command, cwd, refuse):
    check(home, command, cwd, refuse)
