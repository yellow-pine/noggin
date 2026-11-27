"""In Blender, the review file's steps (model/review, #915), each its own process so one finish at a time is in memory:

  blender -b <in.blend> -P model/review/blender.py -- <job.json> <out.blend> assemble | <bone stem> | scenes

assemble: on the Skeleton scene, the Scene Mech swapped for the document (model/skeleton/export.py swap), the finish's
numbers set, the layers made (Mech, Skeleton, Skin and Morty, each in Skull, Mechanism and Pedestal; raw bones to
helpers), coloured at their alpha: the Skin the Shells cut from the Sculpt and the eyeball caps, Morty the private
reference, which the scenes step hides until it is switched on (it shares the Skin's surface). <bone stem>: that bone's finish baked into its mesh. scenes: the motion, then the
Exploded, Print bed and (before) Before and after scenes, linked copies of the same meshes."""

import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, kdtree

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skeleton"))
import export  # noqa: E402

JOB_PATH, OUT, STEP = sys.argv[sys.argv.index("--") + 1 :][:3]
JOB = json.load(open(JOB_PATH))
LAYERS, REGIONS = ("Mech", "Skeleton", "Skin", "Morty"), ("Skull", "Mechanism", "Pedestal")
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
    carriers = m["carriers"]  # skin.MOTION: the one source the Shells ride by too
    fixed = {r for r, c in carriers.items() if c is None}
    if not all(r in carriers for r in roles) or len(set(roles)) != len(roles) or not (fixed | {"head"}) <= set(roles):
        raise ValueError(
            f"review: Morty needs distinct Motion regions of {sorted(carriers)}, head, neck, shoulders and torso among them"
        )
    witnesses = {"witness neck": "neck", "witness L shoulder": "shoulders", "witness R shoulder": "shoulders"}
    if not witnesses.keys() <= {g.name for o in objects for g in o.vertex_groups}:
        raise ValueError("review: local Morty needs independent neck and shoulder vertex witnesses")
    ratio = min(1.0, MORTY_FACES / max(1, sum(len(o.data.polygons) for o in objects)))
    for o in objects:
        carrier = carriers[o["reference_region"]]
        if o.get("carrier", carrier) != carrier:
            raise ValueError(f"review: Morty's {o['reference_region']} names carrier {o['carrier']}, not {carrier}")
        if carrier:
            o["carrier"] = carrier
        if any(witnesses[g.name] != o["reference_region"] for g in o.vertex_groups if g.name in witnesses):
            raise ValueError("review: Morty's independent anatomical witness is in the wrong semantic region")
        if o.get("display_region") not in REGIONS or "part" in o:
            raise ValueError("review: private reference surfaces need a display_region and must not be print parts")
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
        at = Matrix(m["at"]) @ world
        normals = [n.vector.copy() for n in o.data.corner_normals] if o.data.has_custom_normals else []
        o.data.transform(at)
        if normals:
            # Mesh.transform can change thin faces' normal spaces; retain the authored directions.
            normal_at = at.to_3x3().inverted().transposed()
            o.data.normals_split_custom_set([(normal_at @ n).normalized() for n in normals])
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
        if caps:
            clothes = next(i for i, mat in enumerate(o.data.materials) if mat.name == "clothes")
            for f in caps:
                f.material_index = clothes
        bm.to_mesh(o.data)
        bm.free()
        o.color, o.hide_render = (1, 1, 1, JOB["alpha"]["Morty"]), True
    contoured(m, objects)
    bpy.data.collections.remove(source)


VIEWS = {"front": (0, 2), "side": (1, 2)}  # a contour's plane's axes in the head's frame; it sweeps along the third


def ahead(c):
    """A front view's contours cut the face in front of the eyes, not the head's back behind it (the head's frame)."""
    return c.y < 0


def inside(points, poly):
    """Which of the (n, 2) points lie inside the closed polygon (m, 2): even-odd."""
    a = np.asarray(poly)
    b = np.roll(a, -1, axis=0)
    x, y = points[:, :1], points[:, 1:]
    span = (a[:, 1] > y) != (b[:, 1] > y)
    t = (y - a[:, 1]) / np.where(span, b[:, 1] - a[:, 1], 1.0)
    return (span & (x < a[:, 0] + t * (b[:, 0] - a[:, 0]))).sum(axis=1) % 2 == 1


def cut(bm, poly, view, near=lambda c: True):
    """`bm`, in the head's frame, cut along the closed polygon `poly` swept along its view's axis: each side's plane
    through the faces near that side (and `near`), so a face lies on one side of the contour, never across it."""
    i, j = VIEWS[view]
    axis = Vector([float(k not in (i, j)) for k in range(3)])
    piece = bm.faces.layers.int.get("piece") or bm.faces.layers.int.new("piece")
    faces = []
    for f in bm.faces:
        f[piece] = -1
        if near(f.calc_center_median()):
            f[piece] = len(faces)
            faces.append(f)
    if not faces:
        return
    tree, pieces, reach = kdtree.KDTree(len(faces)), {}, 0.0
    for k, f in enumerate(faces):
        c = f.calc_center_median()
        tree.insert((c[i], c[j], 0.0), k)
        pieces[k] = {f}
        reach = max(reach, *(math.hypot(v.co[i] - c[i], v.co[j] - c[j]) for v in f.verts))
    tree.balance()
    for a, b in zip(poly, poly[1:] + poly[:1], strict=True):
        hit = tree.find_range(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0.0), math.dist(a, b) / 2 + reach)
        hit = {f for _, k, _ in hit for f in pieces[k] if f.is_valid}
        p, q = Vector((0, 0, 0)), Vector((0, 0, 0))
        p[i], p[j], q[i], q[j] = *a, *b
        if not hit or (q - p).length < 1e-9:
            continue
        geom = [*hit, *{e for f in hit for e in f.edges}, *{v for f in hit for v in f.verts}]
        done = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=p, plane_no=(q - p).cross(axis).normalized(), dist=1e-6)
        for e in done["geom_cut"]:
            if isinstance(e, bmesh.types.BMEdge):
                for f in e.link_faces:
                    pieces.setdefault(f[piece], set()).add(f)


def contoured(m, objects):
    """#992: each reference surface cut along Morty's cuts on his sculpt (the job's: skin.cuts(), which split the printed
    Shells too) and each face given the Motion region and Colour group it falls in. In front of the eyes, an eye's own
    surface inside its eye white (its dome's foot) is the eye's, all eye white but its pupil, and what is under the mouth
    line the jaw's; the rest of the moving surfaces is the head's, an eye's surface round its dome too (no lid's: the
    lids are the mechanism's covers), its hair above and behind the hairline. On the fixed body, the shirt under the
    collar, the hair above and behind the hairline elsewhere."""
    head, contours, carriers = Matrix(m["head"]), m["contours"], m["carriers"]
    moving = [o for o in objects if carriers[o["reference_region"]] and not o["reference_region"].endswith(" lid")]
    poly = {n: o for n, (_, o) in contours.items()}
    if len({tuple(x.name for x in o.data.materials) for o in moving}) > 1:
        raise ValueError("review: Morty's moving surfaces need the same Colour group slots in the same order")
    shares = {}  # {moving surface: its bmesh, each face's region in the "region" layer, by MOTION order}
    regions = list(carriers)
    for o in objects:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.transform(bm, matrix=head, verts=bm.verts)
        own, names = o["reference_region"], [x.name for x in o.data.materials]
        mine = [f"{own[0]} eye white", f"{own[0]} pupil"] if own.endswith(" eye") else []  # an eye's, on its surface
        cut(bm, poly["hairline"], "side")
        if o in moving:  # the head's, the jaw's and the eyes', which the cuts share out
            for n in (*mine, "mouth"):
                cut(bm, poly[n], "front", ahead)
        else:
            cut(bm, poly["collar"], "side")
        c = np.array([f.calc_center_median() for f in bm.faces]).reshape(-1, 3)
        xz, yz = c[:, [0, 2]], c[:, [1, 2]]
        hair = inside(yz, poly["hairline"])
        if o in moving:
            jaw = (c[:, 1] < 0) & inside(xz, poly["mouth"])
            eye, pupil = ((c[:, 1] < 0) & inside(xz, poly[n]) for n in mine) if mine else (np.zeros(len(c), bool),) * 2
        else:
            shirt = inside(yz, poly["collar"])
        layer = bm.faces.layers.int.new("region")
        for k, f in enumerate(bm.faces):
            region, group = own, "hair" if hair[k] else "face"
            if o not in moving:
                group = "clothes" if shirt[k] else "hair" if hair[k] else "face"
            elif eye[k]:
                group = "pupils" if pupil[k] else "eye whites"
            elif jaw[k]:
                region, group = "jaw", "face"
            else:
                region = "head"
            f[layer], f.material_index = regions.index(region), names.index(group)
        bmesh.ops.transform(bm, matrix=head.inverted(), verts=bm.verts)
        bm.faces.layers.int.remove(bm.faces.layers.int["piece"])
        if o in moving:
            shares[o] = bm
        else:
            bm.faces.layers.int.remove(layer)
            bm.to_mesh(o.data)
            bm.free()
    by_region = {o["reference_region"]: o for o in moving}
    for code, region in enumerate(regions):
        whole = bmesh.new()
        for bm in shares.values():
            part = bm.copy()
            layer = part.faces.layers.int["region"]
            bmesh.ops.delete(part, geom=[f for f in part.faces if f[layer] != code], context="FACES")
            part.faces.layers.int.remove(layer)
            me = bpy.data.meshes.new("share")
            part.to_mesh(me)
            part.free()
            whole.from_mesh(me)
            bpy.data.meshes.remove(me)
        if not whole.faces:
            whole.free()
            if region in by_region:
                raise ValueError(f"review: no face of Morty's reference falls in its {region} region")
            continue
        if region not in by_region:
            raise ValueError(f"review: Morty's reference needs a {region} surface for the faces that fall in it")
        whole.to_mesh(by_region[region].data)
        whole.free()
    for bm in shares.values():
        bm.free()


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
    mech = {o.name.split(".")[0]: o for o in bpy.data.collections[export.MECH].objects}  # a carve copy took the name
    for name, p in JOB["parts"].items():
        o = finished(name.removesuffix(":1")) if p["layer"] == "Skeleton" else mech[name]
        place(o, name, p["region"], p["layer"])
        o.color = lin(p["colour"], JOB["alpha"][p["layer"]])
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
    keyed frame (a Shell with what carries it), Morty with what carries him, and a horn empty per horn keying its
    angle (helpers > Rig)."""
    scene.render.fps, scene.frame_start, scene.frame_end = JOB["fps"], 1, JOB["frames"] - 1  # FRAMES is frame 1 again
    action = bpy.data.actions.new("Review motion")
    rest = JOB_REST
    parts = {o["part"]: o for o in scene.objects if "part" in o}
    for o in objects:
        if carrier := o.get("carrier"):
            if carrier not in parts:
                raise ValueError(f"review: Morty's carrier {carrier} has no live scene object")
            world = o.matrix_world.copy()
            o.parent = parts[carrier]
            o.matrix_parent_inverse = parts[carrier].matrix_world.inverted()
            o.matrix_world = world
    # every moving part: an eyeball cap carries Morty's eye (#969)
    moving = [
        (o, part, o.matrix_world.copy())
        for part, o in parts.items()
        if any(not Matrix(mats[part]) == rest[part] for _, mats in JOB["motion"])
    ]
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
    # the private reference: a toggle, off while the Skin's Shells show the same surface
    main.view_layers[0].layer_collection.children["Morty"].hide_viewport = True
    for w in bpy.context.window_manager.windows:
        w.scene = main
    bounds = [
        o.matrix_world @ Vector(corner)
        for o in main.objects
        if o.type == "MESH" and o.visible_get(view_layer=main.view_layers[0])
        for corner in o.bound_box
    ]
    low = Vector(tuple(min(p[i] for p in bounds) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in bounds) for i in range(3)))
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
