"""`mise run deps` installs frontend/node_modules only when the install is missing or stale (#557).

The test copies the deps task out of the repo's mise.toml into a temp dir, with a stub npm first
on PATH. The real frontend/node_modules is never touched.
"""

import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# npm ci ends by writing node_modules/.package-lock.json; the stub does the same.
STUB_NPM = """#!/bin/sh
echo "$@" >> "$NPM_LOG"
mkdir -p frontend/node_modules/@anthropic-ai/mcpb
: > frontend/node_modules/.package-lock.json
"""


def deps_task():
    lines = (REPO / "mise.toml").read_text().splitlines(keepends=True)
    start = lines.index("[tasks.deps]\n")
    end = start + 1
    while end < len(lines) and not lines[end].startswith("["):
        end += 1
    return "".join(lines[start:end])


def project(tmp_path):
    """A temp project with the real deps task, a lock file and the stub npm."""
    (tmp_path / "mise.toml").write_text(deps_task())
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend/package.json").write_text("{}\n")
    lock = tmp_path / "frontend/package-lock.json"
    lock.write_text("{}\n")
    (tmp_path / "bin").mkdir()
    npm = tmp_path / "bin/npm"
    npm.write_text(STUB_NPM)
    npm.chmod(0o755)
    os.utime(lock, (1000, 1000))
    return lock


def complete_install(tmp_path, mtime=2000):
    """What a finished npm ci leaves behind, with its .package-lock.json at `mtime`."""
    (tmp_path / "frontend/node_modules/@anthropic-ai/mcpb").mkdir(parents=True)
    installed = tmp_path / "frontend/node_modules/.package-lock.json"
    installed.write_text("{}\n")
    os.utime(installed, (mtime, mtime))


def run_deps(tmp_path):
    """Run `mise run deps` in tmp_path; True when the stub npm ran."""
    log = tmp_path / "npm.log"
    env = {
        **os.environ,
        "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "NPM_LOG": str(log),
        "MISE_TRUSTED_CONFIG_PATHS": str(tmp_path),
        "MISE_YES": "1",
    }
    result = subprocess.run(
        ["mise", "run", "deps"], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    return log.exists()


def test_no_node_modules_installs(tmp_path):
    project(tmp_path)
    assert run_deps(tmp_path)


def test_empty_node_modules_installs(tmp_path):
    project(tmp_path)
    (tmp_path / "frontend/node_modules").mkdir()
    assert run_deps(tmp_path)


def test_interrupted_install_installs(tmp_path):
    project(tmp_path)
    (tmp_path / "frontend/node_modules/@anthropic-ai/mcpb").mkdir(parents=True)
    assert run_deps(tmp_path)


def test_lock_newer_than_install_installs(tmp_path):
    lock = project(tmp_path)
    complete_install(tmp_path, mtime=2000)
    os.utime(lock, (3000, 3000))
    assert run_deps(tmp_path)


def test_complete_and_fresh_install_is_kept(tmp_path):
    project(tmp_path)
    complete_install(tmp_path, mtime=2000)
    assert not run_deps(tmp_path)
