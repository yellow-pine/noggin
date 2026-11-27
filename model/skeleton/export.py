"""In Blender, on the Skeleton scene (docs/adr/0025): the Scene Mech swapped for the document model/skeleton job() just
built, every finish run and each bone written as an STL in the head's frame.

  blender -b --factory-startup model/skeleton/skeleton.blend -P model/skeleton/export.py -- <job.json>

build.py imports swap() too, to put the Scene Mech in the scene it builds."""

import json
import os
import struct
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

MECH, CARVE, OPENINGS, FINISHED = "Mech", "Carve", "Openings", "Finished"


def collection(name, parent=None):
    """The collection `name` under `parent` (the scene's), made if missing."""
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if c.name not in parent.children:
        parent.children.link(c)
    return c


def carve(bone, kind):
    """The collection of what the finish of `bone` cuts as `kind` (rigid, moving, skins)."""
    return collection(f"Carve {bone} {kind}", collection(CARVE, collection("helpers")))


def _empty(c):
    for o in list(c.all_objects):
        bpy.data.objects.remove(o)


def _mesh(path, ratio=None):
    """The STL's mesh data (mm), decimated to `ratio` of its faces when given."""
    bpy.ops.wm.stl_import(filepath=path)
    o = bpy.context.selected_objects[0]
    if ratio:
        m = o.modifiers.new("Decimate", "DECIMATE")
        m.ratio = ratio
        with bpy.context.temp_override(object=o):
            bpy.ops.object.modifier_apply(modifier=m.name)
    me = o.data
    bpy.data.objects.remove(o)
    return me


def _box(name, lo, hi, c):
    me = bpy.data.meshes.new(name)
    v = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    me.from_pydata(v, [], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    o = bpy.data.objects.new(name, me)
    c.objects.link(o)
    return o


def swap(job, ratio=None):
    """The Scene Mech and every carve set from `job` (model/skeleton job()): each part at rest in the Mech layer,
    each carving place an object sharing its part's mesh, the skull's openings; `ratio` decimates them (the committed
    scene's light copy). Only the places near each bone's box are linked: the rest can't cut it."""
    _empty(collection(MECH))
    _empty(collection(CARVE, collection("helpers")))
    _empty(collection(OPENINGS, collection("helpers")))
    meshes = {}
    for path in job["files"].values():
        if path not in meshes:
            meshes[path] = _mesh(path, ratio)
            meshes[path].name = os.path.basename(path).removesuffix(".stl")
    frame = Matrix.Translation(job["frame"])
    corners = {path: _corners(me) for path, me in meshes.items()}
    for bone, kinds in job["bones"].items():
        o = bpy.data.objects.get(bone)  # the skull: its bones' collection (model/skeleton/bodyparts.py)
        box = [
            p.matrix_world @ Vector(c)
            for p in ([o] if o else bpy.data.collections[f"{bone} bones"].objects)
            for c in p.bound_box
        ]
        lo = Vector([min(p[i] for p in box) for i in range(3)]) - Vector((2,) * 3)
        hi = Vector([max(p[i] for p in box) for i in range(3)]) + Vector((2,) * 3)
        for kind, places in kinds.items():
            near = []
            for name, at in places:
                m = Matrix(at)
                pts = [m @ Vector(p) for p in corners[job["files"][name]]]
                if all(max(p[i] for p in pts) > lo[i] and min(p[i] for p in pts) < hi[i] for i in range(3)):
                    near.append((name, m))
            # a set with nothing near links one far place, which cuts nothing: an empty set's SDF is empty, and the
            # Finish cut by it leaves no bone (#968: C7, once the jaw's box no longer swept near it)
            # shortcut: a kind with no places at all still links nothing; give it a far dummy if a document has one
            for name, m in near or [(name, Matrix(at)) for name, at in places[:1]]:
                x = bpy.data.objects.new(name, meshes[job["files"][name]])
                x.matrix_world = m
                x.display_type, x.hide_render = "WIRE", True
                carve(bone, kind).objects.link(x)
    mech = collection(MECH)
    for name, path in job["files"].items():
        x = bpy.data.objects.new(name, meshes[path])
        x.matrix_world = Matrix(job["rest"][name])
        mech.objects.link(x)
        x.hide_set(" morty " in name)  # a Skin's Shells hidden: the Skeleton bare
    openings = collection(OPENINGS, collection("helpers"))
    for i, ((x, y, z), r, back) in enumerate(job["orbits"]):  # each orbit a ball, cut off at y `back` where given
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=48, ring_count=24, location=(x, y, z))
        s = bpy.context.active_object
        s.name = f"orbit {i}"
        if back is not None:
            reach = _box("reach", (x - r, y - r, z - r), (x + r, back, z + r), openings)
            cut = s.modifiers.new("Reach", "BOOLEAN")
            cut.operation, cut.object = "INTERSECT", reach
            with bpy.context.temp_override(object=s):
                bpy.ops.object.modifier_apply(modifier=cut.name)
            bpy.data.objects.remove(reach)
        for c in list(s.users_collection):
            c.objects.unlink(s)
        openings.objects.link(s)
    for i, (lo, hi) in enumerate(job["belts"]):
        _box(f"belt {i}", lo, hi, openings)
    for o in openings.objects:
        o.matrix_world = frame @ o.matrix_world  # the job's openings are in the head's frame
        o.display_type, o.hide_render = "WIRE", True


def _corners(me):
    v = [p.co for p in me.vertices]
    lo, hi = [min(p[i] for p in v) for i in range(3)], [max(p[i] for p in v) for i in range(3)]
    return [(a, b, c) for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])]


def _there_and_back(group, grid, name, sign):
    """The SDF `grid` (a socket) offset by `sign` times the group's input `name` (grown by a positive distance, eroded
    by a negative one), then back by as much: the last offset's output, its two nodes named `name` there and back."""
    N, L = group.nodes, group.links
    if name not in group.interface.items_tree:
        group.interface.new_socket(name, in_out="INPUT", socket_type="NodeSocketFloat")
    gi = next(n for n in N if n.bl_idname == "NodeGroupInput")
    for way, by in (("there", sign), ("back", -sign)):
        m = N.new("ShaderNodeMath")
        m.operation = "MULTIPLY"
        L.new(gi.outputs[name], m.inputs[0])
        m.inputs[1].default_value = by
        o = N.new("GeometryNodeSDFGridOffset")
        o.name = f"{name} {way}"
        L.new(grid, o.inputs["Grid"])
        L.new(m.outputs[0], o.inputs["Distance"])
        grid = o.outputs[0]
    return grid


def rounded(group):
    """The skull's Finish (the one cutting the Openings), once, sealed and rounded. Sealed: its bones' SDF grown by
    Seal, then eroded by it, before the shell and the cuts, so BodyParts3D's 21 bones, which only abut (the R maxilla
    stood 1.3 mm off the sphenoid's pterygoid process, and the palate hung on that, #874), are one bone across every
    gap under twice Seal. Rounded: opened by Round before its Mean, eroded, then grown back, so every piece thinner
    than twice Round goes (#838's floor) and every convex edge, the orbits' and the nose's rims among them, comes out
    rounded to it (#993). Older scenes' Finishes get both here, at export; build.py's are born with them."""
    N, L = group.nodes, group.links
    cuts = {n.inputs["Collection"].default_value for n in N if n.bl_idname == "GeometryNodeCollectionInfo"}
    if bpy.data.collections.get(OPENINGS) not in cuts:
        return
    if "Seal there" not in N:
        # the bones' SDF: the one grid read twice, by the shell's outside and its inside
        (bones,) = (
            n.outputs[0] for n in N if n.bl_idname == "GeometryNodeMeshToSDFGrid" and len(n.outputs[0].links) == 2
        )
        into = [link.to_socket for link in bones.links]
        sealed = _there_and_back(group, bones, "Seal", 1.0)
        for socket in into:
            L.new(sealed, socket)
    if "Round there" not in N and "Round erode" not in N:  # "Round erode": a scene saved by an older export
        mean = next(n for n in N if n.bl_idname == "GeometryNodeSDFGridMean")
        L.new(_there_and_back(group, mean.inputs["Grid"].links[0].from_socket, "Round", -1.0), mean.inputs["Grid"])


def numbers(job):
    """The finish's numbers (model/skeleton: PITCH, CLEAR_MM, WALL, KEEP, the skull's Seal and Round) on every
    finish."""
    for o in bpy.data.collections[FINISHED].objects:  # on the modifier: it keeps its own copy of each input
        mod = o.modifiers["Finish"]
        if mod.node_group:  # a Finish not wired yet (the review's stand-in scene) has nothing to round
            rounded(mod.node_group)
        for key, value in job["numbers"].items():
            if key not in ("Seal", "Round") or key in mod.node_group.interface.items_tree:  # the skull's alone
                getattr(mod.properties.inputs, mod.node_group.interface.items_tree[key].identifier).value = value


def _stl(path, me):
    """The mesh as a binary STL at `path`, triangulated (Blender's own exporter evaluates the whole scene again)."""
    me.calc_loop_triangles()
    n = len(me.loop_triangles)
    v = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", v)
    tri = np.empty(n * 3, np.int32)
    me.loop_triangles.foreach_get("vertices", tri)
    rec = np.zeros(n, [("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["v"] = v.reshape(-1, 3)[tri.reshape(-1, 3)]
    with open(path, "wb") as f:
        f.write(b"\0" * 80 + struct.pack("<I", n) + rec.tobytes())


def write(job):
    """Each finished bone's STL in job["out"], moved from the document's frame into the head's."""
    for o in bpy.data.collections[FINISHED].objects:
        o.modifiers["Finish"].show_viewport = True
    dg = bpy.context.evaluated_depsgraph_get()
    back = Matrix.Translation(-Vector(job["frame"]))
    for o in bpy.data.collections[FINISHED].objects:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        me.transform(back @ o.matrix_world)
        stem = o.name.removeprefix("finished ")
        _stl(os.path.join(job["out"], stem + ".stl"), me)
        print(f"export: {stem} {len(me.polygons)} faces", flush=True)


if __name__ == "__main__":
    job = json.load(open(sys.argv[sys.argv.index("--") + 1]))
    swap(job)
    numbers(job)
    write(job)
    print("export: done", flush=True)
    if not bpy.app.background:  # run with its window open (Cansin watches local Blender runs)
        bpy.ops.wm.quit_blender()
