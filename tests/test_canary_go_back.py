"""go-back.sh puts the tagged prev image back and leaves any other image alone."""

import pytest
from test_canary import (
    ASK_PREV,
    ASK_RUNNING,
    IMAGE,
    STEPS,
    WENT_BACK,
    at,
    lines,
    run,
)


def test_go_back_by_hand_puts_prev_in_place_and_points_at_the_readme(tmp_path):
    """By hand: neither PREV_KEPT nor PREV_IMAGE is set."""
    result, calls = run(tmp_path, "go-back.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls[:4] == [ASK_PREV, ASK_RUNNING, *WENT_BACK]
    assert calls[4:]
    assert all(call.startswith("exec blattwerk ") for call in calls[4:])
    (error,) = [line for line in result.stdout.splitlines() if line.startswith("::error::")]
    assert "went back to the prev image" in error
    assert "schema" in error
    assert 'README, "Going back"' in error
    assert result.stdout.endswith("blattwerk answers on the prev image\n")


def test_go_back_without_prev_changes_nothing(tmp_path):
    result, calls = run(tmp_path, "go-back.sh", rc_image=1)
    assert result.returncode == 1
    assert "::error::no prev image" in result.stdout
    assert calls == [ASK_PREV]


def test_go_back_leaves_a_prev_alone_that_this_deploy_did_not_tag(tmp_path):
    result, calls = run(tmp_path, "go-back.sh", prev_kept="")
    assert result.returncode == 1
    assert "::error::prev is not the image that ran before this deploy" in result.stdout
    assert calls == [ASK_PREV]
    # The deploy hands over what keep-prev.sh said.
    assert "PREV_KEPT=$(sed -n 's/^kept=//p' \"$GITHUB_OUTPUT\") \\" in lines()


def test_go_back_goes_back_after_keep_prev_tagged(tmp_path):
    result, calls = run(
        tmp_path, "go-back.sh", prev_kept="yes", prev_image="sha256:old", id_prev="sha256:old"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls[:4] == [ASK_PREV, ASK_RUNNING, *WENT_BACK]


def test_keep_prev_writes_down_the_id_it_tagged(tmp_path):
    output = tmp_path / "output"
    result, calls = run(tmp_path, "keep-prev.sh", github_output=output, id_running="sha256:abc123")
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls[-1] == f"tag sha256:abc123 {IMAGE}:prev"
    assert output.read_text() == "kept=yes\nimage=sha256:abc123\n"
    assert result.stdout == "prev is abc123\n"
    # The deploy hands the id over.
    assert "PREV_IMAGE=$(sed -n 's/^image=//p' \"$GITHUB_OUTPUT\") \\" in lines()
    # And keep-prev.sh writes where the deploy reads.
    assert at("export GITHUB_OUTPUT=$work/output") < at(STEPS[0])


def test_keep_prev_goes_on_and_writes_nothing_down_when_the_tag_fails(tmp_path):
    """An image with no name left cannot be tagged, and the deploy must go on all the same."""
    output = tmp_path / "output"
    result, calls = run(tmp_path, "keep-prev.sh", github_output=output, rc_tag=1)
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls[-1].startswith("tag ")
    assert "::warning::the running image has no name left" in result.stdout
    assert not output.exists()


def test_go_back_leaves_a_prev_alone_that_is_not_the_id_keep_prev_wrote_down(tmp_path):
    result, calls = run(
        tmp_path, "go-back.sh", prev_kept="yes", prev_image="sha256:old", id_prev="sha256:older"
    )
    assert result.returncode == 1
    (error,) = [line for line in result.stdout.splitlines() if line.startswith("::error::")]
    assert "prev is not the image that ran before this deploy" in error
    assert "nothing was changed" in error
    assert "went back" not in result.stdout
    assert calls == [ASK_PREV]


def test_go_back_says_so_when_prev_is_the_image_that_already_runs(tmp_path):
    """A rerun with a cached build: the build is the image that ran, and prev names it too."""
    result, calls = run(
        tmp_path,
        "go-back.sh",
        prev_kept="yes",
        prev_image="sha256:same",
        id_prev="sha256:same",
        id_running="sha256:same",
    )
    assert result.returncode == 1
    (error,) = [line for line in result.stdout.splitlines() if line.startswith("::error::")]
    assert "prev is the image that already runs" in error
    assert "nothing older to go back to" in error
    assert "went back" not in result.stdout
    # No `up`: the container stays. `latest` names what runs again, whatever the deploy made of it.
    assert calls == [ASK_PREV, ASK_RUNNING, WENT_BACK[0]]


def test_go_back_goes_back_when_no_container_is_there(tmp_path):
    result, calls = run(tmp_path, "go-back.sh", rc_inspect=1, id_running="sha256:prev")
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls[:4] == [ASK_PREV, ASK_RUNNING, *WENT_BACK]


@pytest.mark.parametrize(
    "answers",
    [
        {},
        {"rc_image": 1},
        {"prev_kept": ""},
        {"prev_image": "sha256:old"},
        {"id_running": "sha256:prev"},
        {"rc_exec": 1},
    ],
)
def test_go_back_names_no_path(tmp_path, answers):
    """The job log is public."""
    result, _ = run(tmp_path, "go-back.sh", **answers)
    text = result.stdout + result.stderr
    assert str(tmp_path) not in text
    assert "/home" not in text
    assert "/data" not in text


def test_go_back_fails_when_prev_does_not_answer(tmp_path):
    result, calls = run(tmp_path, "go-back.sh", rc_exec=1)
    assert result.returncode == 1
    assert "compose up -d --no-build" in calls
    assert "::error::the prev image does not answer either" in result.stdout
