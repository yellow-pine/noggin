"""GX10 jobs and verified review delivery (#979); private assets never enter git or CI artifacts."""

import argparse
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path


def memory_limit(gib, available):
    """The whole native worker shares this cgroup limit; reserve at least 8 GiB for its host."""
    if gib not in (32, 64):
        raise ValueError("GX10 memory must be 32 or 64 GiB")
    limit = gib * 1024**3
    if available < limit + 8 * 1024**3:
        raise ValueError("insufficient GX10 memory headroom")
    return limit


def blender_ceiling(platform, env):
    """Only the bounded Linux worker receives the larger child-process ceiling."""
    if platform != "linux" or env.get("NOGGIN_GX10_WORKER") != "1":
        return 3_000_000
    ceiling = int(env["NOGGIN_BLENDER_CEILING_KB"])
    if ceiling not in (32 * 1024**2, 64 * 1024**2):
        raise ValueError("GX10 Blender memory must be 32 or 64 GiB")
    return ceiling


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


def begin_review(target, latest, identity):
    """New requests share the publisher's lock, so they cannot race its final stale-job check."""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.with_suffix(".blend.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        atomic_json(latest, identity)


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


def ssh(host, args, **kwargs):
    return subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", host, shlex.join(map(str, args))], **kwargs
    )


def setup(host):
    """The native build is detached once its small toolchain image is ready; reruns resume an active build."""
    repo = Path(__file__).resolve().parent.parent
    pin = re.search(r"^ARG BLENDER=([\d.]+)$", (repo / "ci/blender.Dockerfile").read_text(), re.M)
    assert pin
    version = pin[1]
    if f"fetch blender-{version}.tar.xz " not in (repo / "ci/gx10-blender-build.sh").read_text():
        raise ValueError("the native build source checksums need updating for the CI Blender pin")
    home = ssh(host, ["printenv", "HOME"], check=True, capture_output=True, text=True).stdout.strip()
    tools = f"{home}/noggin-tools/blender-{version}"
    name = f"noggin-blender-{version.replace('.', '')}-build"
    state = ssh(host, ["docker", "inspect", "--format", "{{.State.Status}}", name], capture_output=True, text=True)
    if state.stdout.strip() != "running":
        ssh(host, ["mkdir", "-p", tools], check=True)
        for source, dest in (("gx10-blender.Dockerfile", "Dockerfile"), ("gx10-blender-build.sh", "build.sh")):
            subprocess.run(["scp", "-q", str(repo / "ci" / source), f"{host}:{tools}/{dest}"], check=True)
        ssh(host, ["docker", "build", "-t", f"noggin-blender-build:{version}-arm64", tools], check=True)
        if state.returncode == 0:
            ssh(host, ["docker", "rename", name, f"{name}-{uuid.uuid4().hex[:8]}"], check=True)
        ssh(
            host,
            [
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "--memory=32g",
                "--memory-swap=32g",
                "--cpus=12",
                "--mount",
                f"type=bind,source={tools},target=/work",
                f"noggin-blender-build:{version}-arm64",
                "sh",
                "/work/build.sh",
            ],
            check=True,
        )
    print(f"gx10: native Blender build {name}; docker logs -f {name} on GX10", flush=True)
    while True:
        state = ssh(host, ["docker", "inspect", "--format", "{{json .State}}", name], capture_output=True, text=True)
        if state.returncode == 0:
            status = json.loads(state.stdout)
            if status["Status"] == "exited":
                ssh(host, ["docker", "logs", "--tail", "35", name])
                if status["ExitCode"]:
                    raise RuntimeError(f"native build failed; OOMKilled={status['OOMKilled']}")
                return
        time.sleep(5)


def worker(request_path):
    """Detached host controller: retain the clone lock through computation AND output snapshotting."""
    request_path = Path(request_path).resolve()
    request = json.loads(request_path.read_text())
    root, home = request_path.parent, Path.home()
    result = {"id": request["id"], "commit": request["commit"], "returncode": 1}
    start = time.monotonic()
    try:
        with (home / "noggin.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            repo = home / "noggin"
            if not repo.exists():
                subprocess.run(["git", "clone", "https://github.com/yellow-pine/noggin.git", str(repo)], check=True)
            subprocess.run(["git", "fetch", "-q", "origin", request["branch"]], cwd=repo, check=True)
            subprocess.run(["git", "checkout", "-qf", "--detach", request["commit"]], cwd=repo, check=True)
            version = re.search(r"^ARG BLENDER=([\d.]+)$", (repo / "ci/blender.Dockerfile").read_text(), re.M)
            assert version
            version = version[1]
            result["blender_version"] = version
            tools = home / "noggin-tools" / f"blender-{version}"
            if not (tools / "install/bin/blender").is_file():
                raise RuntimeError(f"native Blender {version} is not installed; run just gx10-setup")
            memory = re.search(r"^MemAvailable:\s+(\d+)", Path("/proc/meminfo").read_text(), re.M)
            assert memory
            available = int(memory[1]) * 1024
            limit = memory_limit(request["memory_gib"], available)
            private, cache = home / "noggin-private", home / "noggin-cache"
            private.mkdir(mode=0o700, exist_ok=True)
            cache.mkdir(mode=0o700, exist_ok=True)
            morty = request.get("morty")
            if morty and checksum(morty["path"]) != morty["sha256"]:
                raise ValueError("private input checksum mismatch")
            name = f"noggin-{request['id']}"
            command = [
                "docker",
                "run",
                "--name",
                name,
                "--memory",
                str(limit),
                "--memory-swap",
                str(limit),
                "--cpus",
                "20",
                "--gpus",
                "all",
                "--user",
                "1000:1000",
                "--workdir",
                str(repo),
            ]
            for source, target, readonly in (
                (repo, repo, False),
                (root, root, False),
                (tools, Path("/work"), True),
                (private, private, True),
                (cache, Path("/cache"), False),
            ):
                command += ["--mount", f"type=bind,source={source},target={target}" + (",readonly" if readonly else "")]
            env = {
                "UV_PROJECT_ENVIRONMENT": "/cache/venv",
                "UV_PYTHON_INSTALL_DIR": "/cache/python",
                "UV_CACHE_DIR": "/cache/uv",
                "UV_LINK_MODE": "copy",
                "PYTHONDONTWRITEBYTECODE": "1",
                "BLENDER": "/work/install/bin/blender",
                "MUJOCO_GL": "egl",
                "NVIDIA_DRIVER_CAPABILITIES": "compute,utility,graphics",
                "NOGGIN_BLENDER_CEILING_KB": str(limit // 1024),
                "NOGGIN_GX10_WORKER": "1",
                "NOGGIN_REVIEW": str(root / "review.blend"),
            }
            if morty:
                env["NOGGIN_MORTY"] = morty["path"]
            for key, value in env.items():
                command += ["--env", f"{key}={value}"]
            executable = "/work/install/bin/blender"
            check = (
                "import bpy; "
                f"assert bpy.app.version == {tuple(map(int, version.split('.')))!r}; "
                "assert bpy.app.build_options.openvdb; "
                "t=bpy.data.node_groups.new('GX10 SDF check','GeometryNodeTree'); "
                "[t.nodes.new(n) for n in ('GeometryNodeMeshToSDFGrid','GeometryNodeSDFGridOffset',"
                "'GeometryNodeSDFGridBoolean','GeometryNodeSDFGridMean')]; "
                "print('gx10: native Blender and SDF nodes verified')"
            )
            flow = shlex.join([executable, "-b", "--factory-startup", "--python-expr", check])
            flow += " && uv sync -q --frozen && " + shlex.join(request["command"])
            if request["review"]:
                flow += " && " + shlex.join(
                    [
                        executable,
                        "-b",
                        "--factory-startup",
                        str(root / "review.blend"),
                        "-P",
                        str(repo / "model/review/verify.py"),
                        "--",
                        str(root / "verification.json"),
                        "1" if morty else "0",
                    ]
                )
            flow += f"; code=$?; cat /sys/fs/cgroup/memory.peak >{shlex.quote(str(root / 'memory.peak'))}; exit $code"
            command += [
                f"noggin-blender-build:{version}-arm64",
                "sh",
                "-c",
                flow,
            ]
            peak = 0
            with (root / "output.log").open("w") as log:
                process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                while process.poll() is None:
                    state = subprocess.run(
                        ["docker", "inspect", "--format", "{{.State.Pid}}", name], capture_output=True, text=True
                    )
                    try:
                        pid = int(state.stdout.strip())
                        group = Path(f"/proc/{pid}/cgroup").read_text().strip().split("::", 1)[1]
                        peak = max(peak, int((Path("/sys/fs/cgroup") / group.lstrip("/") / "memory.peak").read_text()))
                    except (OSError, ValueError, IndexError):
                        pass
                    time.sleep(1)
            if (root / "memory.peak").is_file():
                peak = max(peak, int((root / "memory.peak").read_text()))
            result.update(returncode=process.returncode, peak_memory_bytes=peak, memory_limit_bytes=limit)
            state = subprocess.run(["docker", "inspect", name], capture_output=True, text=True)
            if state.returncode == 0:
                result["oom_killed"] = json.loads(state.stdout)[0]["State"]["OOMKilled"]
                subprocess.run(["docker", "rm", name], check=True, stdout=subprocess.DEVNULL)
            if process.returncode == 0:
                result["files"] = snapshot_outputs(repo, root / "artifacts", request["fetch"])
                if request["review"]:
                    review = root / "review.blend"
                    proof = json.loads((root / "verification.json").read_text())
                    if proof["sha256"] != checksum(review) or proof["version"] != list(map(int, version.split("."))):
                        raise ValueError("saved review identity/version verification failed")
                    result.update(review_verified=True, sha256=proof["sha256"], verification=proof)
    except Exception as error:  # the client needs a terminal result even when setup fails
        result.update(returncode=1, error=str(error))
    result["seconds"] = time.monotonic() - start
    atomic_json(root / "result.json", result)


def submit(host, command, fetch, review=False):
    """Stage immutable inputs, submit a disconnected-safe job, then deliver its immutable result."""
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
    if not branch:
        raise ValueError("gx10 needs a branch with committed work")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    subprocess.run(["git", "push", "-q", "origin", branch], check=True)
    home = ssh(host, ["printenv", "HOME"], check=True, capture_output=True, text=True).stdout.strip()
    job_id = uuid.uuid4().hex
    root = f"{home}/noggin-jobs/{job_id}"
    local = repo / ".cache/gx10" / job_id
    local.mkdir(parents=True, mode=0o700)
    ssh(host, ["mkdir", "-p", root], check=True)
    ssh(host, ["chmod", "700", root], check=True)
    request = {
        "id": job_id,
        "branch": branch,
        "commit": commit,
        "command": command,
        "fetch": fetch,
        "review": review,
        "memory_gib": int(os.environ.get("NOGGIN_GX10_MEMORY_GIB", "32")),
    }
    if request["memory_gib"] not in (32, 64):
        raise ValueError("GX10 memory must be 32 or 64 GiB")
    target = Path(os.environ.get("NOGGIN_REVIEW", Path.home() / "Desktop/noggin-stage3.blend")).resolve()
    latest = target.with_suffix(".blend.request.json")
    if review:
        target.parent.mkdir(parents=True, exist_ok=True)
        begin_review(target, latest, {"id": job_id, "commit": commit})
        common = Path(
            subprocess.check_output(
                ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], text=True
            ).strip()
        ).parent
        source = Path(
            os.environ.get("NOGGIN_MORTY", common / "docs/references/morty/chelscct-morty-smith/morty-review.blend")
        )
        if source.is_file():
            digest = checksum(source)
            folder = f"{home}/noggin-private/inputs/{digest}"
            remote = folder + "/morty-review.blend"
            ssh(host, ["mkdir", "-p", folder], check=True)
            ssh(host, ["chmod", "700", f"{home}/noggin-private", f"{home}/noggin-private/inputs", folder], check=True)
            existing = ssh(host, ["sha256sum", remote], capture_output=True, text=True)
            if existing.returncode or existing.stdout.split()[0] != digest:
                subprocess.run(["scp", "-q", str(source), f"{host}:{remote}.{job_id}.part"], check=True)
                received = ssh(
                    host, ["sha256sum", f"{remote}.{job_id}.part"], check=True, capture_output=True, text=True
                )
                if received.stdout.split()[0] != digest:
                    raise ValueError("private input changed during transfer")
                ssh(host, ["mv", f"{remote}.{job_id}.part", remote], check=True)
                ssh(host, ["chmod", "600", remote], check=True)
            request["morty"] = {"path": remote, "sha256": digest}
    atomic_json(local / "request.json", request)
    subprocess.run(["scp", "-q", str(local / "request.json"), f"{host}:{root}/request.json"], check=True)
    subprocess.run(["scp", "-q", str(Path(__file__).resolve()), f"{host}:{root}/worker.py"], check=True)
    quoted = shlex.quote(root)
    launch = (
        f"nohup python3 {quoted}/worker.py --worker {quoted}/request.json >{quoted}/controller.log 2>&1 </dev/null &"
    )
    ssh(host, ["sh", "-c", launch], check=True)
    print(f"gx10: job {job_id}; log {root}/output.log (continues if disconnected)", flush=True)
    while True:
        status = ssh(host, ["cat", f"{root}/result.json"], capture_output=True, text=True)
        if status.returncode == 0:
            result = json.loads(status.stdout)
            break
        time.sleep(5)
    atomic_json(local / "result.json", result)
    if result["id"] != job_id or result["commit"] != commit:
        raise ValueError("GX10 result identity mismatch")
    if result["returncode"]:
        ssh(host, ["tail", "-n", "30", f"{root}/output.log"])
        raise RuntimeError(f"GX10 failed: {result}")
    if result["files"]:
        subprocess.run(["scp", "-qr", f"{host}:{root}/artifacts", str(local)], check=True)
        for name, digest in result["files"].items():
            source = local / "artifacts" / name
            if checksum(source) != digest:
                raise ValueError(f"result checksum mismatch: {name}")
        for name in result["files"]:
            destination = repo / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(local / "artifacts" / name, destination)
    if review:
        subprocess.run(["scp", "-q", f"{host}:{root}/review.blend", str(local / "review.blend")], check=True)
        publish_review(local / "review.blend", target, latest, result)
    print(
        f"gx10: job {job_id} complete; {result['seconds']:.1f}s, peak {result['peak_memory_bytes'] / 1024**3:.2f} GiB",
        flush=True,
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="gx10")
    parser.add_argument("--fetch", default="")
    parser.add_argument("--review", action="store_true")
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--worker")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.worker:
        worker(args.worker)
        return
    if args.setup:
        setup(args.host)
        return
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if args.review:
        command = ["uv", "run", "just", "_review-build", *command]
    if not command:
        parser.error("a command is required")
    submit(args.host, command, shlex.split(args.fetch), args.review)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"gx10: {error}", file=sys.stderr)
        raise SystemExit(1) from None
