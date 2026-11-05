"""GX10 jobs and verified review delivery (#979); private assets never enter git or CI artifacts."""

import fcntl
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path


def memory_limit(gib, available):
    """The whole native worker shares this cgroup limit; reserve at least 8 GiB for its host."""
    if gib not in (32, 64):
        raise ValueError("GX10 memory must be 32 or 64 GiB")
    limit = gib * 1024**3
    if available < limit + 8 * 1024**3:
        raise ValueError("insufficient GX10 memory headroom")
    return limit


def snapshot_outputs(repo, snapshot, paths):
    """Call while holding the checkout lock; later transfers read only this immutable snapshot."""
    repo, snapshot = Path(repo).resolve(), Path(snapshot)
    manifest = {}
    for relative in paths:
        relative = Path(relative)
        if relative.is_absolute() or ".." in relative.parts or ".git" in relative.parts:
            raise ValueError("FETCH must use repo-relative output paths")
        source = repo / relative
        files = source.rglob("*") if source.is_dir() else [source]
        for path in files:
            if path.is_dir():
                continue
            if not path.resolve().is_relative_to(repo):
                raise ValueError("FETCH must use repo-relative output files")
            name = path.relative_to(repo)
            dest = snapshot / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            manifest[str(name)] = checksum(dest)
    return manifest


def checksum(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def atomic_json(path, value):
    path = Path(path)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as f:
        json.dump(value, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(f.name, path)


def publish_review(candidate, target, latest, verified):
    """Publish only the latest requested, verified result; a failed delivery leaves the last good review intact."""
    candidate, target, latest = Path(candidate), Path(target), Path(latest)
    if not verified.get("review_verified") or checksum(candidate) != verified["sha256"]:
        raise ValueError("review checksum/verification failed")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.with_suffix(".blend.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if json.loads(latest.read_text())["id"] != verified["id"]:
            raise ValueError("review job was superseded")
        backup = None
        if target.exists():
            backup = target.with_name(f".{target.stem}.before-{verified['id']}.blend")
            if not backup.exists():
                with target.open("rb") as source, backup.open("xb") as saved:
                    shutil.copyfileobj(source, saved)
                    saved.flush()
                    os.fsync(saved.fileno())
        with tempfile.NamedTemporaryFile("wb", dir=target.parent, suffix=".blend", delete=False) as saved:
            part = Path(saved.name)
            try:
                with candidate.open("rb") as source:
                    shutil.copyfileobj(source, saved)
                saved.flush()
                os.fsync(saved.fileno())
                if checksum(part) != verified["sha256"]:
                    raise ValueError("review checksum failed during publication")
                os.replace(part, target)
                atomic_json(target.with_suffix(".blend.ready.json"), verified)
            finally:
                part.unlink(missing_ok=True)
        return backup
