"""deploy.sh tries the canary before it touches live, and the workflow sends only the sha."""

import re
import subprocess

import pytest
from test_canary import (
    COMPOSE,
    DEPLOY,
    IMAGE,
    ROOT,
    SAME_IMAGE_SH,
    STEPS,
    WORKFLOW,
    at,
    code,
    jobs,
    lines,
    same_image,
)


def test_deploy_tries_the_canary_before_it_touches_live():
    found = [at(step) for step in STEPS]
    assert found == sorted(found)
    assert "set -euo pipefail" in lines()
    # keep-prev is the first thing the script runs.
    assert at(STEPS[0]) == at("trap finish EXIT") + 1
    # The canary goes pass or fail: a failed start or smoke test is only written down, and ends
    # the run once the stop has run.
    start, smoke, stop, passed = (at(step) for step in STEPS[3:7])
    assert [smoke, stop, passed] == [start + 1, start + 2, start + 3]
    assert "continue-on-error" not in WORKFLOW
    # The pulled image keeps its name `canary`: a registry name that stays must not end the run.
    assert 'docker rmi "$image:$sha" >/dev/null || true' in lines()


def test_latest_moves_only_once_the_canary_passed():
    """After a failed canary `latest` still names the image that runs."""
    promote = f"docker tag {IMAGE}:canary {IMAGE}:latest"
    assert at("[[ $passed == yes ]] || exit 1") < at(promote)
    # Nothing else in the deploy builds, names `latest` or starts the container.
    assert "compose build" not in code(DEPLOY)
    assert "--build" not in code(DEPLOY)
    assert "docker build" not in code(DEPLOY)
    assert [line for line in lines() if "compose up" in line] == [
        "timeout 3m docker compose up -d --no-build"
    ]
    assert code(DEPLOY).count(f"{IMAGE}:latest") == 1
    assert [line for line in lines() if "docker tag" in line] == [
        f'docker tag "$image:$sha" {IMAGE}:canary',
        promote,
    ]
    assert f"{IMAGE}:latest" not in SAME_IMAGE_SH


@pytest.mark.parametrize("running", ["sha256:canary", "sha256:old"], ids=["same id", "other id"])
def test_a_container_with_the_layers_and_config_the_canary_tried_passes(tmp_path, running):
    """A build out of the cache has a new id for the same image, and compose keeps the container."""
    done = same_image(tmp_path, id_running=running)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "::error::" not in done.stdout
    assert running in done.stdout


@pytest.mark.parametrize(
    "answers",
    [
        pytest.param({"layers_running": '["sha256:base","sha256:older"]'}, id="other layers"),
        # A new `ENV` or `CMD` in the Dockerfile adds no layer.
        pytest.param({"config_running": '{"Cmd":["other"]}'}, id="other config"),
        pytest.param({"id_running": ""}, id="no container"),
        pytest.param({"layers_running": "", "config_running": ""}, id="no image of that id"),
        pytest.param({"layers_canary": "", "config_canary": ""}, id="no canary image"),
        # Two inspects that fail give two empty answers, which are not the same image.
        pytest.param(
            {"id_running": "", "layers_canary": "", "config_canary": ""}, id="nothing there"
        ),
        pytest.param({"config_running": "", "config_canary": ""}, id="no config to read"),
    ],
)
def test_a_container_that_kept_the_old_image_fails_the_deploy(tmp_path, answers):
    done = same_image(tmp_path, **answers)
    assert done.returncode == 1, done.stdout + done.stderr
    assert "::error::the blattwerk container does not run the image the canary tried" in done.stdout


def test_every_step_has_an_end_and_the_job_ends_after_them_all():
    """The job's limit must not end the run between `up` and the way back."""
    limits = {}
    for line in lines():
        # A script, the pull, the read of smoke.py, `up` or the live smoke test. One try of
        # alive.sh ends by itself.
        if not re.search(r'(bash|python3) "\$work/|docker (pull|run|compose|exec) ', line):
            continue
        if 'bash "$work/alive.sh"' in line:
            continue
        (limits[line],) = map(int, re.findall(r"^(?:if ! )?timeout (?:-k \d+s )?(\d+)m ", line))
    assert len(limits) == 11
    assert [limit for line, limit in limits.items() if "docker run " in line] == [1]
    assert all(limit > 0 for limit in limits.values())
    # go-back.sh waits a minute for the app, after an `up`.
    (back,) = [limit for line, limit in limits.items() if "go-back.sh" in line]
    assert back >= 2
    # The wait for the app: 30 tries, 2 s apart, and a try gives up after 2 s.
    assert "for _ in $(seq 1 30); do" in lines()
    assert "timeout=2" in (ROOT / "scripts" / "alive.sh").read_text()
    (job,) = map(int, re.findall(r"^    timeout-minutes: (\d+)$", jobs()["deploy"], re.M))
    # Room for that wait and for the lines without a limit: tag, rmi, prune.
    assert sum(limits.values()) + 5 <= job


def test_only_the_way_back_runs_after_a_fail():
    """A failed line ends the script, so a failed canary means no deploy."""
    assert [line for line in lines() if line.startswith("trap ")] == [
        "trap - EXIT",
        "trap finish EXIT",
    ]
    # From the tag step on, not from `up` on: `latest` has moved by then. Not before it: the old
    # container is untouched and there is nothing to go back from.
    assert [line for line in lines() if line.startswith("promoted=")] == [
        "promoted=",
        "promoted=yes",
    ]
    assert at("promoted=yes") == at(f"docker tag {IMAGE}:canary {IMAGE}:latest") - 1
    assert "if [[ $status != 0 && -n $promoted ]]; then" in lines()
    (back,) = [line for line in lines() if "go-back.sh" in line and not line.startswith("cp ")]
    # A way back that fails must not hide the status of the deploy.
    assert back == 'timeout 3m bash "$work/go-back.sh" || true'
    assert at("if [[ $status != 0") < at(back) < at('exit "$status"') < at("trap finish EXIT")


def test_the_live_smoke_test_is_the_read_only_half():
    (live,) = [line for line in lines() if "--read-only" in line]
    call = "docker exec -i blattwerk /app/.venv/bin/python - --read-only http://127.0.0.1:8000"
    assert live == f'timeout 2m {call} <"$work/smoke.py"'
    # The invite makes a user: canary.sh does that, and deploy.sh gives it no way to the live app.
    assert "SMOKE_INVITE" not in code(DEPLOY)
    assert "invite" not in code(DEPLOY)
    assert code(DEPLOY).count("--read-only") == 1


def test_the_smoke_test_comes_out_of_the_image_it_tests():
    read = f"docker run --rm --init --network none --entrypoint cat {IMAGE}:canary"
    # TERM alone does not end a `docker run`: the first process of a container gets no signal
    # it has no handler for. `--init` puts one before `cat` that hands it on, and KILL follows.
    assert f'if ! timeout -k 10s 1m {read} /app/scripts/smoke.py >"$work/smoke.py"; then' in lines()
    assert "COPY scripts/smoke.py ./scripts/smoke.py\n" in (ROOT / "Dockerfile").read_text()
    # No copy of it lies beside the scripts on the VPS.
    (copied,) = [line for line in lines() if line.startswith("cp ")]
    assert "smoke.py" not in copied


def test_deploy_and_compose_name_the_same_data_folder():
    """A folder moved in one file only would snapshot nothing, or try the canary on no data."""
    (mounted,) = re.findall(r"^ +- (\S+):/data$", COMPOSE, re.M)
    (live,) = re.findall(r"^live=(\S+)$", code(DEPLOY), re.M)
    (copy,) = re.findall(r"^copy=(\S+)$", code(DEPLOY), re.M)
    assert live == mounted
    assert copy == f"{mounted}-canary"
    (snapshot,) = re.findall(r'snapshot\.py" (\S+)/blattwerk\.db" ', code(DEPLOY))
    assert snapshot == '"$live'
    canary = re.findall(r'canary\.sh" (start|stop) (\S+) (\S+)', code(DEPLOY))
    assert canary == [("start", '"$live"', '"$copy"'), ("stop", '"$live"', '"$copy"')]


def test_the_build_has_an_end():
    (limit,) = map(int, re.findall(r"^    timeout-minutes: (\d+)$", jobs()["build"], re.M))
    assert limit == 20


def test_no_job_runs_on_the_vps_and_the_deploy_job_sends_only_the_sha():
    """Nothing of a commit runs on the box but its image."""
    assert list(jobs()) == ["build", "deploy"]
    assert "self-hosted" not in code(WORKFLOW)
    assert "continue-on-error" not in WORKFLOW
    for job in jobs().values():
        assert re.findall(r"^    runs-on: (.+)$", job, re.M) == ["ubuntu-latest"]
    build, deploy = jobs()["build"], jobs()["deploy"]
    sha = "${{ github.event.workflow_run.head_sha }}"
    # The image deploy.sh pulls is the one the build pushed.
    (image,) = re.findall(r"^image=(\S+)$", code(DEPLOY), re.M)
    assert f"          tags: {image}:{sha}\n" in build
    assert f"          ref: {sha}\n" in build
    assert "          persist-credentials: false\n" in build
    # No checkout and no action: the job runs no file of the repo.
    assert "uses:" not in deploy
    assert "scripts/" not in deploy
    assert "    needs: build\n" in deploy
    assert "    environment: vps\n" in deploy
    assert "    permissions: {}\n" in deploy
    assert f"          SHA: {sha}\n" in deploy
    assert re.findall(r"^          ssh .*$", deploy, re.M) == [
        "          ssh -i ~/.ssh/deploy -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes"
        ' "$DEPLOY_HOST" "$SHA"'
    ]
    assert deploy.rstrip().endswith('"$DEPLOY_HOST" "$SHA"')


# ── every script ──


@pytest.mark.parametrize("script", sorted(path.name for path in (ROOT / "scripts").glob("*.sh")))
def test_script_parses(script):
    result = subprocess.run(
        ["bash", "-n", str(ROOT / "scripts" / script)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
