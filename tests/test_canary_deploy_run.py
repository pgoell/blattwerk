"""A deploy run puts the image the canary tried live, and a failure goes back to prev."""

from test_canary import (
    PULLED,
    SHA,
    SMOKE,
    TRIED,
    WENT_BACK,
    WENT_LIVE,
    deploy,
)


def test_a_deploy_puts_the_image_live_that_the_canary_tried(tmp_path):
    result, did, names = deploy(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert did == [*PULLED, *TRIED, *WENT_LIVE, "image prune -f"]
    # The registry's name is gone again, and `prev` names the image that ran before.
    assert names == {
        "runs": "sha256:new",
        "latest": "sha256:new",
        "canary": "sha256:new",
        "prev": "sha256:old",
    }
    # The canary was fed the smoke test that came out of the image.
    assert (tmp_path / "docker.log.smoke").read_text() == SMOKE
    assert "::error::" not in result.stdout
    assert result.stdout.endswith(f"blattwerk runs {SHA}\n")


def test_a_failed_canary_leaves_latest_and_the_container_as_they_were(tmp_path):
    result, did, names = deploy(tmp_path, rc_canary=1)
    assert result.returncode == 1
    # The canary and the copy go all the same, and nothing after them runs: no way back either.
    assert did == [*PULLED, *TRIED]
    assert names["latest"] == names["runs"] == "sha256:old"
    # The failed image stays for a look.
    assert names["canary"] == "sha256:new"


def test_an_image_without_a_smoke_test_fails_before_the_canary(tmp_path):
    """An image from before the Dockerfile copied scripts/smoke.py into it."""
    result, did, names = deploy(tmp_path, rc_run=1)
    assert result.returncode == 1
    assert "::error::the image holds no /app/scripts/smoke.py" in result.stdout
    assert did == PULLED
    assert names["latest"] == names["runs"] == "sha256:old"


def test_a_failed_live_smoke_test_goes_back_to_prev(tmp_path):
    result, did, names = deploy(tmp_path, rc_live=1)
    # The status of the deploy, not of the way back, which passed.
    assert result.returncode == 1
    # No prune: the failed image stays for a look.
    assert did == [*PULLED, *TRIED, *WENT_LIVE, *WENT_BACK]
    assert names["latest"] == names["runs"] == names["prev"] == "sha256:old"
    assert "::error::the deploy failed and went back to the prev image" in result.stdout
    assert result.stdout.endswith("blattwerk answers on the prev image\n")
