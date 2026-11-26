"""Read the completed review in Blender before it can be published by the GX10 controller (#979)."""

import hashlib
import json
import math
import os
import sys
from pathlib import Path

import bpy

report, require_morty = sys.argv[sys.argv.index("--") + 1 :]
required = {"Assembled", "Exploded", "Print bed"}
assert required <= {s.name for s in bpy.data.scenes}, "review scenes missing"
assembled = bpy.data.scenes["Assembled"]
assert assembled.frame_end > assembled.frame_start, "review motion range missing"
assert "Review motion" in bpy.data.actions, "review action missing"
counts = {}
for name in ("Mech", "Skeleton", "Morty"):
    collection = bpy.data.collections.get(name)
    assert collection is not None, f"review layer missing: {name}"
    meshes = [o for o in collection.all_objects if o.type == "MESH"]
    if name != "Morty" or require_morty == "1":
        assert meshes, f"review layer empty: {name}"
    counts[name] = len(meshes)
    for obj in meshes:
        assert len(obj.data.vertices) and len(obj.data.polygons), f"empty review mesh: {obj.name}"
        assert all(math.isfinite(x) for v in obj.data.vertices for x in v.co), f"nonfinite review mesh: {obj.name}"
        assert all(math.isfinite(x) for row in obj.matrix_world for x in row), f"nonfinite placement: {obj.name}"
with open(bpy.data.filepath, "rb") as source:
    checksum = hashlib.file_digest(source, "sha256").hexdigest()
out = {
    "version": list(bpy.app.version),
    "sha256": checksum,
    "scenes": sorted(required),
    "mesh_counts": counts,
    "finite_nonempty_meshes": True,
    "motion_frames": [assembled.frame_start, assembled.frame_end],
    "private_reference_required": require_morty == "1",
}
with Path(report).open("w") as target:
    json.dump(out, target)
    target.flush()
    os.fsync(target.fileno())
print("review: verified saved Blender file", flush=True)
