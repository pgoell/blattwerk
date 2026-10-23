"""The frontend build stays put when the sources' bytes do not change (#256).

mise records the size and timestamp of each source. A new timestamp fails that check
before the age of the build is considered, so the build runs even when it is newer than
every source. Side-by-side ``mise run test:webkit`` then each start vite, and vite empties
``src/blattwerk/static`` first: one dies with ENOTEMPTY on ``fonts/andika``.

The task hashes contents. The build script holds one lock until npm exits.
"""

import os
import shutil
import subprocess
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# npm run build ends by writing the output the task named; the stub does the same.
STUB_NPM = """#!/bin/sh
echo vite build >> "$NPM_LOG"
mkdir -p out
echo built > out/index.html
"""

# What two vite builds do to one tree: each empties it, then writes fonts/andika.
STUB_RACE = """#!/bin/sh
echo start >> "$NPM_LOG"
mkdir -p static/fonts/andika
echo x > static/fonts/andika/a
sleep 0.3
rm -rf static
mkdir -p static/fonts/andika
echo y > static/fonts/andika/a
echo end >> "$NPM_LOG"
"""


def repo_config():
    return tomllib.loads((REPO / "mise.toml").read_text())


def project(tmp_path):
    """A temp project with the repo's content-hash setting and a stub npm."""
    flag = repo_config()["settings"]["task"]["source_freshness_hash_contents"]
    assert flag is True
    (tmp_path / "mise.toml").write_text(
        "[settings]\n"
        f"task.source_freshness_hash_contents = {str(flag).lower()}\n"
        "\n"
        "[tasks.build]\n"
        'sources = ["src.txt"]\n'
        'outputs = ["out/index.html"]\n'
        'run = "npm run build"\n'
    )
    src = tmp_path / "src.txt"
    src.write_text("same\n")
    os.utime(src, (1000, 1000))
    (tmp_path / "bin").mkdir()
    npm = tmp_path / "bin/npm"
    npm.write_text(STUB_NPM)
    npm.chmod(0o755)
    return src


def env_for(tmp_path):
    log = tmp_path / "npm.log"
    return {
        **os.environ,
        "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "NPM_LOG": str(log),
        "MISE_TRUSTED_CONFIG_PATHS": str(tmp_path),
        "MISE_YES": "1",
        "MISE_STATE_DIR": str(tmp_path / "state"),
    }, log


def run_build(tmp_path, env):
    return subprocess.run(
        ["mise", "run", "build"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )


def prime(tmp_path, env, log):
    """The first run has no stored hash, so it builds and leaves the output in place."""
    result = run_build(tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert log.read_text().splitlines() == ["vite build"]
    return tmp_path / "out/index.html"


def older_than(path, than):
    ns = than.stat().st_mtime_ns - 5_000_000_000
    os.utime(path, ns=(ns, ns))


def test_a_new_timestamp_with_the_same_bytes_does_not_rebuild(tmp_path):
    src = project(tmp_path)
    env, log = env_for(tmp_path)
    out = prime(tmp_path, env, log)
    older_than(src, out)
    result = run_build(tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert log.read_text().splitlines() == ["vite build"]
    assert "sources up-to-date" in result.stderr


def test_side_by_side_runs_with_the_same_bytes_do_not_rebuild(tmp_path):
    """Same bytes skip the build when several runs overlap.

    A fresh check rewrites ``state/task-sources/*-content`` with the same bytes.
    The rewrite truncates the file, and a parallel read can see it empty and run
    the task. Each run here reads the baseline the first run finished writing.
    """
    src = project(tmp_path)
    env, log = env_for(tmp_path)
    out = prime(tmp_path, env, log)
    older_than(src, out)
    state = tmp_path / "state"
    procs = []
    for index in range(4):
        copy = tmp_path / f"state-{index}"
        shutil.copytree(state, copy)
        procs.append(
            subprocess.Popen(
                ["mise", "run", "build"],
                cwd=tmp_path,
                env={**env, "MISE_STATE_DIR": str(copy)},
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        )
    for proc in procs:
        out_text, _ = proc.communicate()
        assert proc.returncode == 0, out_text
        assert "sources up-to-date" in out_text
    assert log.read_text().splitlines() == ["vite build"]


def test_new_bytes_rebuild_even_at_an_old_timestamp(tmp_path):
    src = project(tmp_path)
    env, log = env_for(tmp_path)
    out = prime(tmp_path, env, log)
    src.write_text("changed\n")
    older_than(src, out)
    result = run_build(tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert log.read_text().splitlines() == ["vite build", "vite build"]


def test_a_missing_build_is_rebuilt(tmp_path):
    project(tmp_path)
    env, log = env_for(tmp_path)
    out = prime(tmp_path, env, log)
    out.unlink()
    result = run_build(tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert log.read_text().splitlines() == ["vite build", "vite build"]
    assert out.is_file()


def test_side_by_side_builds_do_not_empty_the_output_together(tmp_path):
    """The script, not mise, keeps two builds that do run from emptying one tree."""
    build = repo_config()["tasks"]["build"]
    assert build["run"] == "python3 scripts/build_frontend.py"
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    script = scripts / "build_frontend.py"
    script.write_text((REPO / "scripts/build_frontend.py").read_text())
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    npm = bin_dir / "npm"
    npm.write_text(STUB_RACE)
    npm.chmod(0o755)
    log = tmp_path / "npm.log"
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "NPM_LOG": str(log),
    }
    procs = [
        subprocess.Popen(
            ["python3", str(script)],
            cwd=tmp_path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for _ in range(4)
    ]
    for proc in procs:
        out_text, _ = proc.communicate()
        assert proc.returncode == 0, out_text
    assert log.read_text().splitlines() == ["start", "end"] * 4
