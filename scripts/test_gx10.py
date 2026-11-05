"""GX10 delivery retains the last good review until the requested, verified result is ready."""

import fcntl
import hashlib
import json
import shutil
import stat
import subprocess
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from scripts import gx10
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


def test_a_reset_transfer_retries_even_if_ssh_recovers_immediately(monkeypatch):
    copies, sleeps = [], []
    outcomes = iter([255, 0])

    def copy(command):
        copies.append(command)
        return SimpleNamespace(returncode=next(outcomes))

    monkeypatch.setattr(gx10.subprocess, "run", copy)
    monkeypatch.setattr(gx10, "ssh", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    monkeypatch.setattr(gx10.time, "sleep", sleeps.append)
    gx10.transfer("gx10", "candidate.blend", "/private/candidate.part", upload=True)
    assert copies == [["scp", "-q", "candidate.blend", "gx10:/private/candidate.part"]] * 2
    assert sleeps == [5]


def test_a_reachable_transfer_error_is_reported(monkeypatch):
    monkeypatch.setattr(gx10.subprocess, "run", lambda *args: SimpleNamespace(returncode=1))
    monkeypatch.setattr(gx10, "ssh", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    with pytest.raises(RuntimeError, match="reachable"):
        gx10.transfer("gx10", "/private/result.blend", "candidate.blend")


def test_private_fit_inputs_are_immutable_and_changed_inputs_stage_separately(tmp_path, monkeypatch):
    remote, source = tmp_path / "remote", tmp_path / "fit-data.npz"
    source.write_bytes(b"original private fit data")
    monkeypatch.setattr(gx10, "ssh", lambda host, args, **kw: subprocess.run(args, **kw))
    monkeypatch.setattr(gx10, "transfer", lambda host, src, dest, **kw: shutil.copyfile(src, dest))
    first = gx10.stage_inputs("gx10", remote, {"NOGGIN_PRIVATE_FIT": source}, "first")
    staged = first["NOGGIN_PRIVATE_FIT"]
    path = gx10.Path(staged["path"])
    assert path.read_bytes() == b"original private fit data"
    assert staged["sha256"] == hashlib.sha256(b"original private fit data").hexdigest()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    source.write_bytes(b"changed private fit data")
    second = gx10.stage_inputs("gx10", remote, {"NOGGIN_PRIVATE_FIT": source}, "second")
    assert second["NOGGIN_PRIVATE_FIT"]["path"] != staged["path"]
    assert path.read_bytes() == b"original private fit data"


def test_a_measured_32_gib_oom_retries_once_at_64_and_retains_both_attempts():
    calls = []

    def native_job(gib):
        calls.append(gib)
        return {"id": "same-job", "commit": "same-source", "returncode": 137, "oom_killed": True, "memory_gib": gib}

    result = gx10.bounded_attempts(32, native_job)
    assert calls == [32, 64]
    assert result["id"] == "same-job" and result["commit"] == "same-source"
    assert [a["memory_gib"] for a in result["attempts"]] == [32, 64]


def test_a_geometry_error_does_not_request_more_memory():
    calls = []

    def native_job(gib):
        calls.append(gib)
        return {"returncode": 1, "oom_killed": False}

    gx10.bounded_attempts(32, native_job)
    assert calls == [32]


def test_retry_stops_if_fresh_headroom_cannot_support_64_gib():
    available = iter([100 * 1024**3, 70 * 1024**3])
    launched = []

    def native_job(gib):
        try:
            memory_limit(gib, next(available))
        except ValueError as error:
            return {"returncode": 1, "error": str(error)}
        launched.append(gib)
        return {"returncode": 137, "oom_killed": True}

    result = gx10.bounded_attempts(32, native_job)
    assert launched == [32]
    assert "headroom" in result["error"]
    assert len(result["attempts"]) == 2
