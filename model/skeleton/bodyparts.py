"""In Blender, once (#874): the Skeleton scene's bones became BodyParts3D 4.0's, in place of 3Demon's skull and the
atlas-axis (docs/adr/0023, 0025). Kept as the record of how, like build.py. From the #872 prototype's scene (its
Basis: the original meshes posed in the bust's frame, decimated, sources.json naming each one's FJ element) it takes
the skull's 21 bones (the collection `skull bones`, which the skull's Finishes read whole), the mandible and C1 to C7
(the atlas, the axis, c3 to c7) with their Basis, Warp and Sculpt keys, and the Landmarks the fit reads; it drops the
old bones, points each Finish at its new bone (copying the atlas's for c3 to c7) and swaps in the Scene Mech.
rewarp.py then writes the Warp (`just rewarp`).

  blender -b --factory-startup model/skeleton/skeleton.blend -P model/skeleton/bodyparts.py -- <prototype.blend> \
      <job.json> <out.blend>

job.json: model/skeleton job()."""

import json
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export  # noqa: E402

PROTOTYPE, JOB, OUT = sys.argv[sys.argv.index("--") + 1 :][:3]
SOURCES = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources.json")))["objects"]
NECK = {"C1": "atlas", "C2": "axis", **{f"C{i}": f"c{i}" for i in range(3, 8)}}
LANDMARKS = ("LM L orbit", "LM R orbit", "LM L condyle", "LM R condyle", "LM menton")
SKULL_BONES = "skull bones"

job = json.load(open(JOB))
for name in ("skull", "mandible", "atlas", "axis"):  # 3Demon's and the atlas-axis's
    o = bpy.data.objects.get(name)
    if o:
        me = o.data
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(me)
for o in list(bpy.data.collections["Landmarks"].objects):
    bpy.data.objects.remove(o)

with bpy.data.libraries.load(PROTOTYPE, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n in SOURCES or n in LANDMARKS]
skull = export.collection("Skull", export.collection("Skeleton"))
bones = export.collection(SKULL_BONES, skull)
for o in dst.objects:
    if o.name in LANDMARKS:
        bpy.data.collections["Landmarks"].objects.link(o)
        continue
    o.name = o.data.name = NECK.get(o.name, o.name)
    (skull if o.name in ("mandible", *NECK.values()) else bones).objects.link(o)
    keys = o.data.shape_keys.key_blocks
    keys["Sculpt"].relative_key = keys["Warp"]
    keys["Warp"].value = keys["Sculpt"].value = 1.0
    at = o.matrix_world.copy()
    o.parent = None
    o.matrix_world = at


def point(group, bone):
    """The Finish `group` reads `bone`: the skull's bones as a collection, any other bone as its object."""
    N, L = group.nodes, group.links
    info = next(n for n in N if n.bl_idname == "GeometryNodeObjectInfo")
    if bone != "skull":
        info.inputs["Object"].default_value = bpy.data.objects[bone]
        return
    c = N.new("GeometryNodeCollectionInfo")
    c.transform_space = "RELATIVE"
    c.inputs["Collection"].default_value = bones
    c.inputs["Separate Children"].default_value = False
    r = N.new("GeometryNodeRealizeInstances")
    L.new(c.outputs[0], r.inputs[0])
    for link in list(info.outputs["Geometry"].links):
        L.new(r.outputs[0], link.to_socket)
    N.remove(info)


finished = bpy.data.collections[export.FINISHED]
for o in finished.objects:
    stem = o.name.removeprefix("finished ")
    point(o.modifiers["Finish"].node_group, next((b for b, w in job["worn"].items() if w == stem), stem))
atlas = bpy.data.objects["finished atlas"]
for i in range(3, 8):
    stem = f"c{i}"
    group = atlas.modifiers["Finish"].node_group.copy()
    group.name = f"Finish {stem}"
    point(group, stem)
    for n in group.nodes:
        if n.bl_idname == "GeometryNodeCollectionInfo":
            kind = n.inputs["Collection"].default_value.name.rsplit(" ", 1)[1]
            n.inputs["Collection"].default_value = export.carve(stem, kind)
    o = bpy.data.objects.new(f"finished {stem}", bpy.data.meshes.new(f"finished {stem}"))
    finished.objects.link(o)
    mod = o.modifiers.new("Finish", "NODES")
    mod.node_group = group
    mod.show_viewport = False

export.swap(job, ratio=0.1)
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT), compress=True)
print("bodyparts: done", flush=True)
if not bpy.app.background:
    bpy.ops.wm.quit_blender()
