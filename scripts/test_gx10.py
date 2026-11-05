"""GX10 delivery retains the last good review until the requested, verified result is ready."""

import fcntl
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from scripts.gx10 import begin_review, blender_ceiling, memory_limit, publish_review, snapshot_outputs


def delivery(tmp_path):
    candidate, target = tmp_path / "candidate.blend", tmp_path / "noggin-stage3.blend"
    candidate.write_bytes(b"complete Blender candidate")
    target.write_bytes(b"last good review")
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps({"id": "current"}))
    verified = {"id": "current", "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(), "review_verified": True}
    return candidate, target, latest, verified


def test_a_corrupt_transfer_cannot_replace_the_last_good_review(tmp_path):
    candidate, target, latest, verified = delivery(tmp_path)
    candidate.write_bytes(b"interrupted transfer")
    with pytest.raises(ValueError, match="checksum"):
        publish_review(candidate, target, latest, verified)
    assert target.read_bytes() == b"last good review"
    assert not target.with_suffix(".blend.ready.json").exists()


def test_a_late_old_job_cannot_replace_a_newer_requested_review(tmp_path):
    candidate, target, latest, verified = delivery(tmp_path)
    verified["id"] = "old"
    with pytest.raises(ValueError, match="superseded"):
        publish_review(candidate, target, latest, verified)
    assert target.read_bytes() == b"last good review"


def test_a_verified_current_result_is_published_with_its_backup_and_receipt(tmp_path):
    candidate, target, latest, verified = delivery(tmp_path)
    backup = publish_review(candidate, target, latest, verified)
    assert target.read_bytes() == candidate.read_bytes()
    assert backup is not None
    assert backup.read_bytes() == b"last good review"
    assert json.loads(target.with_suffix(".blend.ready.json").read_text()) == verified


def test_results_remain_immutable_after_the_shared_checkout_changes(tmp_path):
    repo, snapshot = tmp_path / "repo", tmp_path / "snapshot"
    output = repo / "model/build/result.txt"
    output.parent.mkdir(parents=True)
    output.write_text("job one")
    manifest = snapshot_outputs(repo, snapshot, ["model/build/result.txt"])
    output.write_text("job two")
    assert (snapshot / "model/build/result.txt").read_text() == "job one"
    assert manifest["model/build/result.txt"] == hashlib.sha256(b"job one").hexdigest()


def test_remote_limits_leave_system_headroom_and_keep_the_approved_ceiling():
    assert memory_limit(32, 48 * 1024**3) == 32 * 1024**3
    with pytest.raises(ValueError, match="headroom"):
        memory_limit(64, 70 * 1024**3)
    with pytest.raises(ValueError, match="32 or 64"):
        memory_limit(96, 117 * 1024**3)


def test_a_fetch_cannot_escape_the_job_snapshot(tmp_path):
    with pytest.raises(ValueError, match="relative"):
        snapshot_outputs(tmp_path, tmp_path / "out", ["../secret"])


def test_a_remote_limit_cannot_raise_the_mac_blender_ceiling():
    env = {"NOGGIN_GX10_WORKER": "1", "NOGGIN_BLENDER_CEILING_KB": str(32 * 1024**2)}
    assert blender_ceiling("darwin", env) == 3_000_000
    assert blender_ceiling("linux", env) == 32 * 1024**2
    env["NOGGIN_BLENDER_CEILING_KB"] = str(96 * 1024**2)
    with pytest.raises(ValueError, match="32 or 64"):
        blender_ceiling("linux", env)


def test_a_new_request_waits_for_an_in_progress_publication(tmp_path):
    _, target, latest, _ = delivery(tmp_path)
    with target.with_suffix(".blend.lock").open("a") as lock, ThreadPoolExecutor(max_workers=1) as pool:
        fcntl.flock(lock, fcntl.LOCK_EX)
        request = pool.submit(begin_review, target, latest, {"id": "newer"})
        try:
            with pytest.raises(TimeoutError):
                request.result(timeout=0.1)
            assert json.loads(latest.read_text()) == {"id": "current"}
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
        request.result(timeout=5)
    assert json.loads(latest.read_text()) == {"id": "newer"}


def test_an_empty_promised_output_is_a_failure(tmp_path):
    repo = tmp_path / "repo"
    (repo / "model/build/finished").mkdir(parents=True)
    with pytest.raises(ValueError, match="empty"):
        snapshot_outputs(repo, tmp_path / "snapshot", ["model/build/finished"])
