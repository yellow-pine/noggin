"""In Blender, the review file's steps (model/review, #915), each its own process so one finish at a time is in memory:

  blender -b <in.blend> -P model/review/blender.py -- <job.json> <out.blend> assemble | <bone stem> | scenes

assemble: on the Skeleton scene, the Scene Mech swapped for the document (model/skeleton/export.py swap), the finish's
numbers set, the layers made (Mech, Skeleton, Morty, each in Skull, Mechanism and Pedestal; Shells and raw bones to
helpers), coloured at their alpha. <bone stem>: that bone's finish baked into its mesh. scenes: the motion, then the
Exploded, Print bed and (before) Before and after scenes, linked copies of the same meshes."""

import json
import os
import sys

import bmesh
import bpy
from mathutils import Matrix

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skeleton"))
import export  # noqa: E402

JOB_PATH, OUT, STEP = sys.argv[sys.argv.index("--") + 1 :][:3]
JOB = json.load(open(JOB_PATH))
LAYERS, REGIONS = ("Mech", "Skeleton", "Morty"), ("Skull", "Mechanism", "Pedestal")
MORTY_FACES = 100_000  # the sculpt decimated to about this many
bpy.context.preferences.filepaths.save_version = 0  # no .blend1 beside the file


def lin(hexc, alpha):
    c = [int(hexc[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    return (*[x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c], alpha)


def material(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = rgba
    return m


def paint(o):
    """Per-object slots: mirrored parts share meshes, and each scene's copies keep their own alpha."""
    m = material("Review " + ",".join(f"{v:.6f}" for v in o.color), o.color)
    if not o.data.materials:
        o.data.materials.append(m)
    for slot in o.material_slots:
        slot.link, slot.material = "OBJECT", m


def finished(stem):
    return bpy.data.objects[f"finished {stem}"]


def place(o, part, region, layer):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    bpy.data.collections[f"{layer} {region}"].objects.link(o)
    o["part"] = part


def morty(m):
    """Private semantic surfaces, painted by Colour group and carried by live parts; fixed body surfaces never key.
    The editable source stays local and is read without being rewritten."""
    with bpy.data.libraries.load(m["blend"]) as (src, dst):
        if "Morty reference" not in src.collections:
            raise ValueError("review: local Morty needs an editable Morty reference collection with semantic meshes")
        dst.collections = ["Morty reference"]
    source = dst.collections[0]
    objects = [o for o in source.all_objects if o.type == "MESH"]
    roles = [o.get("reference_region") for o in objects]
    fixed = {"neck", "shoulders", "torso"}
    if (
        not all(isinstance(r, str) and r for r in roles)
        or len(set(roles)) != len(roles)
        or not (fixed | {"head"}) <= set(roles)
    ):
        raise ValueError("review: Morty needs distinct head, neck, shoulders and torso surfaces")
    witnesses = {"witness neck": "neck", "witness L shoulder": "shoulders", "witness R shoulder": "shoulders"}
    if not witnesses.keys() <= {g.name for o in objects for g in o.vertex_groups}:
        raise ValueError("review: local Morty needs independent neck and shoulder vertex witnesses")
    ratio = min(1.0, MORTY_FACES / max(1, sum(len(o.data.polygons) for o in objects)))
    for o in objects:
        carrier = o.get("carrier")
        if any(witnesses[g.name] != o["reference_region"] for g in o.vertex_groups if g.name in witnesses):
            raise ValueError("review: Morty's independent anatomical witness is in the wrong semantic region")
        if o.get("display_region") not in REGIONS or "part" in o:
            raise ValueError("review: private reference surfaces need a display_region and must not be print parts")
        if (o["reference_region"] in fixed and carrier) or (o["reference_region"] not in fixed and not carrier):
            raise ValueError("review: neck, shoulders and torso stay fixed; moving surfaces need a live carrier")
        if carrier and carrier not in JOB_REST:
            raise ValueError(f"review: Morty's carrier {carrier} is absent from the live model")
        if not o.data.polygons or not o.data.materials:
            raise ValueError("review: local Morty surfaces need painted meshes")
        for slot in o.material_slots:
            if not slot.material or slot.material.name not in m["colours"]:
                raise ValueError("review: local Morty materials must be named by Skin Colour group")
            slot.material.diffuse_color = lin(m["colours"][slot.material.name], JOB["alpha"]["Morty"])
        world = o.matrix_world.copy()
        for c in list(o.users_collection):
            c.objects.unlink(o)
        bpy.data.collections[f"Morty {o['display_region']}"].objects.link(o)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        o.data = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        o.modifiers.clear()
        if ratio < 1.0:
            dec = o.modifiers.new("Decimate", "DECIMATE")
            dec.ratio = ratio
            with bpy.context.temp_override(object=o, active_object=o):
                bpy.ops.object.modifier_apply(modifier=dec.name)
        o.parent = None
        o.animation_data_clear()
        o.matrix_world = Matrix.Identity(4)
        o.data.transform(Matrix(m["at"]) @ world)
        bm = bmesh.new()
        bm.from_mesh(o.data)
        floor = m["floor"]
        bmesh.ops.bisect_plane(
            bm,
            geom=[*bm.verts, *bm.edges, *bm.faces],
            plane_co=(0, 0, floor),
            plane_no=(0, 0, 1),
            clear_inner=True,
            dist=1e-5,
        )
        rim = [e for e in bm.edges if e.is_boundary and all(abs(v.co.z - floor) < 1e-4 for v in e.verts)]
        caps = bmesh.ops.holes_fill(bm, edges=rim)["faces"]
        if any(e.is_boundary for e in rim):
            raise ValueError("review: Morty's floor cannot be capped; close the local reference's arm/base cuts first")
        clothes = next(i for i, mat in enumerate(o.data.materials) if mat.name == "clothes")
        for f in caps:
            f.material_index = clothes
        bm.to_mesh(o.data)
        bm.free()
        o.color, o.hide_render = (1, 1, 1, JOB["alpha"]["Morty"]), True
    bpy.data.collections.remove(source)


def assemble():
    export.swap(JOB)
    export.numbers(JOB)
    helpers = export.collection("helpers")
    for layer in LAYERS:
        top = export.collection(layer)
        for region in REGIONS:
            export.collection(f"{layer} {region}", top)
    for c in ("Skull", export.FINISHED):  # out of Skeleton: the raw bones to helpers, the finished ones to regions
        bpy.data.collections["Skeleton"].children.unlink(bpy.data.collections[c])
    helpers.children.link(bpy.data.collections["Skull"])
    shells = export.collection("Shells", helpers)
    mech = {o.name.split(".")[0]: o for o in bpy.data.collections[export.MECH].objects}  # a carve copy took the name
    for name, p in JOB["parts"].items():
        o = finished(name.removesuffix(":1")) if p["layer"] == "Skeleton" else mech[name]
        if p["layer"] is None:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            shells.objects.link(o)
            o["part"] = name
        else:
            place(o, name, p["region"], p["layer"])
        o.color = lin(p["colour"], JOB["alpha"][p["layer"] or "Mech"])
        paint(o)
        o.hide_set(False)
    for o in list(bpy.data.collections[export.FINISHED].objects):  # the bare copies: the document wears the worn
        bpy.data.objects.remove(o)
    bpy.data.collections.remove(bpy.data.collections[export.FINISHED])
    if JOB["morty"]:
        morty(JOB["morty"])
    else:
        print("review: no local sectioned Morty reference (NOGGIN_MORTY); his layer stays empty", flush=True)


def bake(stem):
    """The bone's finish evaluated alone (at rest) and baked into its own mesh, the modifier dropped."""
    bpy.context.scene.frame_set(1)
    o = finished(stem)
    mod = o.modifiers["Finish"]
    mod.show_viewport = True
    me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    o.modifiers.remove(mod)
    old, o.data = o.data, me
    me.name = o.name
    bpy.data.meshes.remove(old)
    paint(o)
    print(f"review: {stem} {len(me.polygons)} faces", flush=True)


def walk(lc):
    yield lc
    for c in lc.children:
        yield from walk(c)


def shading(s):
    s.render.engine = "BLENDER_WORKBENCH"
    s.display.shading.light, s.display.shading.color_type = "STUDIO", "MATERIAL"
    s.unit_settings.scale_length, s.unit_settings.length_unit = 0.001, "MILLIMETERS"


def animate(scene, objects):
    """One looping action ("Review motion", a slot per object): each part where the document's pose puts it every
    keyed frame, Morty with what carries him, and a horn empty per horn keying its angle (helpers > Rig)."""
    scene.render.fps, scene.frame_start, scene.frame_end = JOB["fps"], 1, JOB["frames"] - 1  # FRAMES is frame 1 again
    action = bpy.data.actions.new("Review motion")
    rest = JOB_REST
    moving = []
    for o in objects:
        part = o.get("part") or o.get("carrier")
        if part and any(not Matrix(mats[part]) == rest[part] for _, mats in JOB["motion"]):
            moving.append((o, part, o.matrix_world.copy()))
    for o, _, _ in moving:
        o.rotation_mode = "QUATERNION"
        o.animation_data_create().action = action
    for frame, mats in JOB["motion"]:
        for o, part, w0 in moving:
            o.matrix_world = Matrix(mats[part]) @ rest[part].inverted() @ w0
            o.keyframe_insert("location", frame=frame)
            o.keyframe_insert("rotation_quaternion", frame=frame)
    rig = export.collection("Rig", export.collection("helpers"))
    for horn, pts in JOB["horns"].items():
        e = bpy.data.objects.new(f"horn {horn}", None)
        rig.objects.link(e)
        e.animation_data_create().action = action
        for frame, deg in pts:
            e["deg"] = deg
            e.keyframe_insert('["deg"]', frame=frame)
    scene.frame_set(1)


def copies(scene, name, items):
    """Linked copies (the same mesh data) of each (object, 4x4 world) in a new collection `name` of `scene`."""
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    for o, world in items:
        x = o.copy()
        x.animation_data_clear()
        x.parent = None
        x.matrix_world = world
        x.color = (*x.color[:3], 1.0)
        for slot in x.material_slots:
            if slot.material:
                m = slot.material
                slot.link, slot.material = "OBJECT", material(m.name + " opaque", (*m.diffuse_color[:3], 1.0))
        x.hide_render = False
        c.objects.link(x)
        x.hide_set(False)
    return c


def new_scene(name):
    s = bpy.data.scenes.new(name)
    shading(s)
    s.frame_start = s.frame_end = 1
    return s


def scenes():
    main = bpy.context.scene
    main.name = "Assembled"
    shading(main)
    for lc in walk(main.view_layers[0].layer_collection):
        if lc.name == "helpers":
            lc.hide_viewport = True
            lc.collection.hide_render = True
    parts = {o["part"]: o for o in bpy.data.objects if "part" in o}
    layered = [o for layer in LAYERS for o in bpy.data.collections[layer].all_objects]
    world = {n: o.matrix_world.copy() for n, o in parts.items()}  # at rest, before the motion
    animate(main, layered)
    exploded = new_scene("Exploded")
    for layer in LAYERS[:2]:
        items = [(parts[n], Matrix.Translation(p["offset"]) @ world[n]) for n, p in JOB["parts"].items()]
        copies(exploded, f"Exploded {layer}", [(o, w) for o, w in items if JOB["parts"][o["part"]]["layer"] == layer])
    bed = new_scene("Print bed")
    side, gap = JOB["bed"]
    on = {}
    for n, (i, m) in JOB["plates"].items():
        on.setdefault(i, []).append((parts[n], Matrix(m) @ world[n]))  # m moves the rest-placed part
    plate = bpy.data.materials.new("Print plate")
    plate.diffuse_color = (0.08, 0.08, 0.09, 1.0)
    for i, items in sorted(on.items()):
        c = copies(bed, f"Plate {i + 1}", items)
        me = bpy.data.meshes.new(f"plate {i + 1}")
        x0 = i * (side + gap)
        me.from_pydata([(x0 + x, y, -1.0) for x in (0, side) for y in (0, side)], [], [(0, 2, 3, 1)])
        me.materials.append(plate)
        p = bpy.data.objects.new(f"Plate {i + 1} ({side:.0f} x {side:.0f} mm)", me)
        p.color = plate.diffuse_color
        c.objects.link(p)
    if JOB["before"]:
        both = new_scene("Before and after")
        with bpy.data.libraries.load(JOB["before"]) as (src, dst):
            dst.collections = ["Skull"]
        before = dst.collections[0]
        after = [(o, o.matrix_world.copy()) for o in bpy.data.collections["Skull"].objects]
        copies(
            both,
            "Before (main)",
            [(o, Matrix.Translation((-JOB["beside"], 0, 0)) @ o.matrix_world) for o in before.objects],
        )
        copies(both, "After (this branch)", after)
        bpy.data.collections.remove(before)
    for s in bpy.data.scenes:  # each scene's matrix_world, else stale until it is shown
        s.view_layers[0].update()
    for w in bpy.context.window_manager.windows:
        w.scene = main
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                sp = area.spaces.active
                sp.shading.type, sp.shading.color_type = "SOLID", "MATERIAL"
                sp.clip_start, sp.clip_end = 1.0, 20000.0


JOB_REST = {n: Matrix(m) for n, m in JOB["motion"][0][1].items()}
if STEP == "assemble":
    assemble()
elif STEP == "scenes":
    scenes()
else:
    bake(STEP)
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT), compress=True)
print("review: done", flush=True)
