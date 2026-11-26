"""In Blender, the latest file (model/latest, #998) from each layer's candidate, as the review assembled it:

  blender -b --factory-startup -P model/latest/blender.py -- <latest.json> <out.blend>

One scene, Latest, at rest: a collection per layer named for it and its candidate's label (the whole label in its
`label` property, a failed export's reason in `reason`), holding that candidate's collection: Mech (Mechanism), the
raw warped bones (Skeleton: its own Skeleton scene's Skull), Morty (Skin reference) and Shells (Skin Shells). Each
candidate's objects are taken into its own head's frame, so layers from different branches line up at the head."""

import json
import sys

import bpy
from mathutils import Matrix, Vector

JOB_PATH, OUT = sys.argv[sys.argv.index("--") + 1 :][:2]
JOB = json.load(open(JOB_PATH))
SOURCE = {"Mechanism": "Mech", "Skeleton": "Skull", "Skin reference": "Morty", "Skin Shells": "Shells"}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0  # no .blend1 beside the file
scene = bpy.context.scene
scene.name = "Latest"
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light, scene.display.shading.color_type = "STUDIO", "MATERIAL"
scene.unit_settings.scale_length, scene.unit_settings.length_unit = 0.001, "MILLIMETERS"

for layer, source in SOURCE.items():
    c = JOB["layers"][layer]
    label = c["label"] + (f" (empty: {c['reason']})" if c["reason"] else "")
    top = bpy.data.collections.new(f"{layer}: {label}"[:63])  # Blender's name limit; the whole label is a property
    top["layer"], top["label"], top["reason"] = layer, label, c["reason"] or ""
    scene.collection.children.link(top)
    if not c["blend"]:
        continue
    with bpy.data.libraries.load(c["blend"]) as (src, dst):
        dst.collections = [source] if source in src.collections else []
    if not dst.collections:
        top.name, top["reason"] = f"{layer}: no {source} in its file"[:63], f"no {source} collection in {c['blend']}"
        continue
    got = dst.collections[0]
    top.children.link(got)
    back = Matrix(json.load(open(c["job"]))["head"]).inverted()  # the candidate's document into its head's frame
    bpy.context.view_layer.update()  # each object's world from its basis and parents (a saved one may be stale)
    for o in list(got.all_objects):
        world = o.matrix_world.copy()
        o.parent = None  # a parent outside the collection (a pose empty) is not kept
        o.animation_data_clear()
        o.matrix_basis = back @ world
        o.hide_set(False)

scene.view_layers[0].update()
bounds = [o.matrix_world @ Vector(k) for o in scene.objects if o.type == "MESH" for k in o.bound_box]
low = Vector(tuple(min((p[i] for p in bounds), default=-100) for i in range(3)))
high = Vector(tuple(max((p[i] for p in bounds), default=100) for i in range(3)))
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            sp = area.spaces.active
            sp.shading.type, sp.shading.color_type = "SOLID", "MATERIAL"
            sp.clip_start, sp.clip_end = 1.0, 20000.0
            sp.region_3d.view_perspective = "ORTHO"
            sp.region_3d.view_rotation = Vector((1, -1, 1)).to_track_quat("Z", "Y")
            sp.region_3d.view_location = (low + high) * 0.5
            sp.region_3d.view_distance = max((high - low).length * 1.2, 10.0)
            sp.overlay.show_overlays = False
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print("review: done", flush=True)
