"""The canary's smoke test receives the invite, and stop removes the canary and the copy."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import os

import pytest
from test_canary import (
    NAME,
    SMOKE,
    copy,  # noqa: F401
    live,  # noqa: F401
    run,
    tree,
)

# ── canary.sh smoke ──


@pytest.mark.parametrize("answer", [0, 1])
def test_smoke_hands_the_invite_over_in_the_environment(tmp_path, answer):
    result, calls = run(tmp_path, "canary.sh", "smoke", rc_smoke=answer)
    assert result.returncode == answer
    assert calls == [
        f"exec {NAME} /app/.venv/bin/python -m blattwerk invite",
        f"exec -i -e SMOKE_INVITE {NAME} /app/.venv/bin/python - http://127.0.0.1:8000",
    ]
    log = tmp_path / "docker.log"
    assert log.with_name("docker.log.invite").read_text() == "/einladung/tok123\n"
    assert log.with_name("docker.log.stdin").read_text() == SMOKE
    assert "tok123" not in "\n".join(calls)
    assert "tok123" not in result.stdout + result.stderr
    assert "smoke ran" in result.stdout


def test_smoke_fails_without_an_invite(tmp_path):
    result, calls = run(tmp_path, "canary.sh", "smoke", rc_invite=1)
    assert result.returncode == 1
    assert "::error::" in result.stdout
    assert "tok123" not in result.stdout + result.stderr
    assert len(calls) == 1


# ── canary.sh stop ──


def test_stop_removes_the_canary_and_the_copy(tmp_path, live, copy):
    assert run(tmp_path, "canary.sh", "start", live, copy)[0].returncode == 0
    before = tree(live)
    result, calls = run(tmp_path, "canary.sh", "stop", live, copy)
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls == [f"rm -f {NAME}"]
    assert not copy.exists()
    assert tree(live) == before


@pytest.mark.skipif(os.geteuid() == 0, reason="root deletes anywhere")
def test_stop_that_cannot_delete_the_copy_fails_and_names_no_file(tmp_path, live, copy):
    assert run(tmp_path, "canary.sh", "start", live, copy)[0].returncode == 0
    locked = copy / "users" / "1" / "uploads"
    locked.chmod(0o500)
    try:
        result, _ = run(tmp_path, "canary.sh", "stop", live, copy)
    finally:
        locked.chmod(0o700)
    assert result.returncode == 1
    assert "::error::" in result.stdout
    assert "uploads" not in result.stdout + result.stderr
    assert str(copy) not in result.stdout + result.stderr


def test_stop_is_fine_when_nothing_is_there(tmp_path, live, copy):
    # docker says 1 when there is no such container.
    result, calls = run(tmp_path, "canary.sh", "stop", live, copy, rc_rm=1)
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls == [f"rm -f {NAME}"]
    assert result.stdout + result.stderr == ""
