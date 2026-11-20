"""`just rewarp`: public Bone exchange to GX10, under both existing resource locks; private Morph stays local."""

import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

from model import skeleton
from model.review import SLOT, _blender, lock


def run():
    source, script = Path(skeleton.SCENE).resolve(), Path(__file__).with_name("rewarp.py").resolve()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    host = os.environ.get("NOGGIN_GX10", "gx10")
    with tempfile.TemporaryDirectory(prefix="noggin-warp-") as directory:
        prefix = str(Path(directory) / "public-bones")
        held = lock(SLOT, wait=True)
        try:
            _blender([str(source), "-P", str(script), "--", "export", prefix])
        finally:
            held.close()
        remote_dir = subprocess.check_output(["ssh", host, "mktemp", "-d"], text=True).strip()
        assert remote_dir.startswith("/") and not any(c.isspace() for c in remote_dir)
        remote = remote_dir + "/public-bones"
        subprocess.run(["scp", prefix + ".npz", host + ":" + remote + ".npz"], check=True)
        subprocess.run(["scp", prefix + ".json", host + ":" + remote + ".json"], check=True)
        out = "model/build/fit/" + digest
        subprocess.run(
            [
                "just",
                f"GX10={host}",
                f"FETCH={out}.npz {out}.json",
                "gx10",
                "uv",
                "run",
                "python",
                "-m",
                "model.skeleton.fit",
                "--landmarks",
                remote + ".npz",
                remote + ".json",
                out,
            ],
            check=True,
        )
        assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, (
            "Scene changed during the solve; kept it untouched"
        )
        held = lock(SLOT, wait=True)
        try:
            candidate = str(Path(directory) / "skeleton.blend")
            _blender([str(source), "-P", str(script), "--", "apply", str(Path(out).resolve()), candidate])
            assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, (
                "Scene changed during application; kept it untouched"
            )
            os.replace(candidate, source)
        finally:
            held.close()


if __name__ == "__main__":
    run()
