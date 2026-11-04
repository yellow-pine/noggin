"""Blender's public Bone exchange for the GX10 warp; no numerical solve or private mesh export here.

blender -b skeleton.blend -P rewarp.py -- export <prefix>
blender -b skeleton.blend -P rewarp.py -- apply <prefix> <out.blend>
`just rewarp` coordinates both under the existing Blender and GX10 locks.
"""

import hashlib
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector


def coordinates(data):
    points = np.empty(len(data) * 3)
    data.foreach_get("co", points)
    return points.reshape(-1, 3)


def export(prefix):
    """Only the licensed source inventory's raw Basis/Warp/Sculpt and sparse anatomical Landmarks."""
    inventory = json.load(open(os.path.join(os.path.dirname(__file__), "sources.json")))["objects"]
    arrays, scene = {}, {"bones": [], "landmarks": {}}
    if "warp_blend" in bpy.context.scene:
        scene["warp_blend"] = json.loads(bpy.context.scene["warp_blend"])
    if "anatomical_regions" in bpy.context.scene:
        scene["anatomical_regions"] = json.loads(bpy.context.scene["anatomical_regions"])
    groups = {"Skull", "Mandible", "Ribcage"} | {f"C{i}" for i in range(1, 8)}
    for name in inventory:
        o = bpy.data.objects[name]
        key = f"b{len(scene['bones'])}"
        group = next(c.name for c in o.users_collection if c.name in groups)
        for kind in ("Basis", "Warp", "Sculpt"):
            arrays[f"{key}_{kind.lower()}"] = coordinates(o.data.shape_keys.key_blocks[kind].data)
        o.data.calc_loop_triangles()
        arrays[key + "_faces"] = np.array([t.vertices[:] for t in o.data.loop_triangles], dtype=np.int32)
        scene["bones"].append({"name": name, "key": key, "group": group, "matrix": list(map(list, o.matrix_world))})
    for o in bpy.data.collections["Landmarks"].all_objects:
        if not o.name.endswith(" target") and not o.hide_get():
            target = bpy.data.objects.get(o.name + " target", o)
            scene["landmarks"][o.name] = {
                "source": list(o.matrix_world.translation),
                "target": list(target.matrix_world.translation),
                "region": o.get("warp_region", "shared"),
            }
    np.savez_compressed(prefix + ".npz", **arrays)
    with open(prefix + ".json", "w") as f:
        json.dump(scene, f, indent=2)


def apply(prefix, out):
    """Apply a validated public result without altering Basis; the coordinator replaces the source atomically."""
    scene, arrays = json.load(open(prefix + ".json")), np.load(prefix + ".npz")
    report = scene["fit_report"]
    assert report["min_jacobian"] > 0.1 and report["landmark_error_mm"] <= 1.0, report
    inventory = json.load(open(os.path.join(os.path.dirname(__file__), "sources.json")))["objects"]
    assert {b["name"] for b in scene["bones"]} == set(inventory)
    assert set(report["regional_stretch"]) == set(inventory), "Missing confirmed regional/Sculpt deformation proof"
    for bone in report["regional_stretch"].values():
        for kind in ("field", "surface_including_sculpt"):
            assert bone[kind]["minimum"] >= 0.75 - 1e-6 and bone[kind]["maximum"] <= 1.25 + 1e-6
    basis = {}
    for bone in scene["bones"]:
        o = bpy.data.objects[bone["name"]]
        keys = o.data.shape_keys.key_blocks
        basis[o.name] = hashlib.sha256(coordinates(keys["Basis"].data).tobytes()).digest()
        matrix = np.asarray(bone["matrix"])
        assert matrix.shape == (4, 4) and np.isfinite(matrix).all()
        o.matrix_world = Matrix(matrix)
        for kind in ("Warp", "Sculpt"):
            points = arrays[f"{bone['key']}_{kind.lower()}"]
            assert points.shape == (len(o.data.vertices), 3) and np.isfinite(points).all()
            keys[kind].data.foreach_set("co", points.ravel())
            keys[kind].value = 1.0
        o.data.update()
    landmarks = bpy.data.collections["Landmarks"]
    for name, pair in scene["landmarks"].items():
        for suffix, kind in (("", "source"), (" target", "target")):
            o = bpy.data.objects.get(name + suffix)
            if o is None:
                o = bpy.data.objects.new(name + suffix, None)
                landmarks.objects.link(o)
            o.matrix_world.translation = Vector(pair[kind])
            o["warp_region"] = pair.get("region", "shared")
            o.hide_set(False)
    for o in landmarks.all_objects:
        if not o.name.endswith(" target") and o.name not in scene["landmarks"]:
            o.hide_set(True)
    for name, digest in basis.items():
        points = coordinates(bpy.data.objects[name].data.shape_keys.key_blocks["Basis"].data)
        assert hashlib.sha256(points.tobytes()).digest() == digest, name
    bpy.context.scene["fit_report"] = json.dumps(report)
    bpy.context.scene["anatomical_regions"] = json.dumps(scene["anatomical_regions"])
    if "warp_blend" in scene:
        bpy.context.scene["warp_blend"] = json.dumps(scene["warp_blend"])
    elif "warp_blend" in bpy.context.scene:
        del bpy.context.scene["warp_blend"]
    if "bone_parts" in bpy.context.scene:
        sys.path.insert(0, os.path.dirname(__file__))
        import adopt

        adopt.refresh()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out), compress=True)
    assert os.path.getsize(out) <= 12_000_000, "Skeleton scene exceeds its 12 MB cap"


if __name__ == "__main__":
    action, prefix, *rest = sys.argv[sys.argv.index("--") + 1 :]
    if action == "export":
        export(prefix)
    else:
        assert action == "apply" and len(rest) == 1
        apply(prefix, rest[0])
    print("review: done", flush=True)
