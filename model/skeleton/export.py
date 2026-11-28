"""In Blender, on the Skeleton scene (docs/adr/0025): the Scene Mech swapped for the document model/skeleton job() just
built, every finish run and each bone written as an STL in the head's frame.

  blender -b --factory-startup model/skeleton/skeleton.blend -P model/skeleton/export.py -- <job.json>

build.py imports swap() too, to put the Scene Mech in the scene it builds."""

import json
import math
import os
import struct
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

MECH, CARVE, OPENINGS, FINISHED, VAULT = "Mech", "Carve", "Openings", "Finished", "Vault"
CAP, BOSSES, POCKETS, BALLS, GROOVES = "Cap", "Cap bosses", "Cap pockets", "Cap balls", "Cap grooves"  # #874
SEAM = ("seam above", "seam below")  # the seam's cutters: what the skull loses, what its cap loses


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


def _cap(cap, frame, lo, hi):
    """The cap's helpers (job["cap"], the head's frame at `frame` in the document's, #874): the seam's two cutters,
    each a box over the skull's (`lo` to `hi`), one from the skull's face of the seam up and one from its cap's face
    down, the gap between them; at each Seat a ball boss on the seam and one pocket through both faces, a magnet
    deep in each, and round it three balls on the skull's face (spared by its cutter, so they stand on it) and their
    three V-grooves up into the cap's (a Seat's two halves, as model/printed/skin.py draws them)."""
    c = collection(CAP, collection("helpers"))
    z, half = frame.z + cap["seam"], cap["gap"] / 2
    above = _box(SEAM[0], (lo.x, lo.y, z - half), hi, bpy.context.scene.collection)  # in view: a modifier is applied
    _box(SEAM[1], lo, (hi.x, hi.y, z + half), c)
    (bore, depth), (ring, ball), (reach, deep) = cap["bore"], cap["ball"], cap["groove"]
    w = deep + 1.0  # a groove's cutter: its edge `deep` into the cap, 45 deg each side down past the cap's face
    wedge = [(r, t, h) for r in (ring - reach, ring + reach) for t, h in ((-w, -1.0), (w, -1.0), (0.0, deep))]
    for i, (x, y) in enumerate(cap["seats"]):
        at = Vector((frame.x + x, frame.y + y, z))
        bpy.ops.mesh.primitive_uv_sphere_add(radius=cap["boss"], segments=48, ring_count=24, location=at)
        _into(bpy.context.active_object, collection(BOSSES, c))
        bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=bore, depth=2 * (half + depth), location=at)
        _into(bpy.context.active_object, collection(POCKETS, c))
        for deg in (0, 120, 240):
            turn = Matrix.Rotation(math.radians(deg), 4, "Z")
            on = at + turn @ Vector((ring, 0, -half))  # on the skull's face
            bpy.ops.mesh.primitive_uv_sphere_add(radius=ball, segments=32, ring_count=16, location=on)
            _into(bpy.context.active_object, collection(BALLS, c))
            me = bpy.data.meshes.new(f"groove {i} {deg}")
            me.from_pydata(wedge, [], [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (0, 3, 5, 2)])
            groove = bpy.data.objects.new(me.name, me)
            groove.matrix_world = Matrix.Translation(at + Vector((0, 0, half))) @ turn
            collection(GROOVES, c).objects.link(groove)
    spare = above.modifiers.new("Balls", "BOOLEAN")  # the skull keeps what its cutter spares
    spare.operation, spare.operand_type, spare.collection = "DIFFERENCE", "COLLECTION", collection(BALLS, c)
    with bpy.context.temp_override(object=above):
        bpy.ops.object.modifier_apply(modifier=spare.name)
    _into(above, c)
    for o in c.all_objects:
        o.display_type, o.hide_render = "WIRE", True


def _into(o, c):
    for old in list(o.users_collection):
        old.objects.unlink(o)
    c.objects.link(o)


def swap(job, ratio=None):
    """The Scene Mech and every carve set from `job` (model/skeleton job()): each part at rest in the Mech layer,
    each carving place an object sharing its part's mesh, the skull's openings and its cap's helpers; `ratio`
    decimates them (the committed scene's light copy). Only the places near each bone's box are linked: the rest
    can't cut it."""
    _empty(collection(MECH))
    _empty(collection(CARVE, collection("helpers")))
    _empty(collection(OPENINGS, collection("helpers")))
    _empty(collection(CAP, collection("helpers")))
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
        if bone in job["cap"]["of"]:
            _cap(job["cap"], Vector(job["frame"]), lo, hi)
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
    vault = collection(VAULT, collection("helpers"))  # the vault's bones once more, for the Finish to thicken
    for name in job["vault"]["bones"]:
        if name not in vault.objects:
            vault.objects.link(bpy.data.objects[name])


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


def _all(group, c):
    """The collection's objects as one geometry (a socket), each where it stands."""
    N, L = group.nodes, group.links
    info = N.new("GeometryNodeCollectionInfo")
    info.transform_space = "RELATIVE"
    info.inputs["Collection"].default_value = c
    info.inputs["Separate Children"].default_value = False
    real = N.new("GeometryNodeRealizeInstances")
    L.new(info.outputs[0], real.inputs[0])
    return real.outputs[0]


def _grid(group, geometry):
    """The mesh `geometry` (a socket) as an SDF grid at the group's Voxel, its band the group's other grids'."""
    N, L = group.nodes, group.links
    (band,) = {n.inputs["Band Width"].default_value for n in N if n.bl_idname == "GeometryNodeMeshToSDFGrid"}
    sdf = N.new("GeometryNodeMeshToSDFGrid")
    L.new(geometry, sdf.inputs["Mesh"])
    L.new(next(n for n in N if n.bl_idname == "NodeGroupInput").outputs["Voxel"], sdf.inputs["Voxel Size"])
    sdf.inputs["Band Width"].default_value = band
    return sdf.outputs[0]


def _thickened(group, bones, middle):
    """The bones' SDF `bones` (a socket) united with the vault's bones (the Vault collection) once more, each vertex
    moved toward `middle` (the cranium's, in the Finish's own frame) by what the bone lacks there of the group's input
    Thick (a ray through the bone, against its normal, measures it), half of that and all of it: a bone of the vault
    thinner than Thick comes out Thick, inward, its outer side where it was, and a thicker one unchanged. Two steps,
    so the seal after it closes what is left between a thin sheet and its copies."""
    N, L = group.nodes, group.links
    if "Thick" not in group.interface.items_tree:
        group.interface.new_socket("Thick", in_out="INPUT", socket_type="NodeSocketFloat")
    gi = next(n for n in N if n.bl_idname == "NodeGroupInput")

    def vector(operation, *sockets):
        n = N.new("ShaderNodeVectorMath")
        n.operation = operation
        for i, s in enumerate(sockets):
            L.new(s, n.inputs["Scale" if operation == "SCALE" and i else i])
        return n

    def number(operation, a, b):
        n = N.new("ShaderNodeMath")
        n.operation = operation
        for socket, value in zip(n.inputs, (a, b)):
            if isinstance(value, float):
                socket.default_value = value
            else:
                L.new(value, socket)
        return n.outputs[0]

    real = _all(group, bpy.data.collections[VAULT]).node
    position = N.new("GeometryNodeInputPosition").outputs[0]
    into = vector("SCALE", N.new("GeometryNodeInputNormal").outputs[0])  # against the normal: through the bone
    into.inputs["Scale"].default_value = -1.0
    start = vector("SCALE", into.outputs[0])
    start.inputs["Scale"].default_value = 0.05  # off its own face
    ray = N.new("GeometryNodeRaycast")
    L.new(real.outputs[0], ray.inputs["Target Geometry"])
    L.new(vector("ADD", position, start.outputs[0]).outputs[0], ray.inputs["Source Position"])
    L.new(into.outputs[0], ray.inputs["Ray Direction"])
    lacks = number("MAXIMUM", number("SUBTRACT", gi.outputs["Thick"], ray.outputs["Hit Distance"]), 0.0)
    inward = N.new("ShaderNodeVectorMath")
    inward.operation = "SUBTRACT"
    inward.inputs[0].default_value = middle
    L.new(position, inward.inputs[1])
    unit = vector("NORMALIZE", inward.outputs[0])
    band = bones.node.inputs["Band Width"].default_value  # the bones' own Mesh to SDF Grid's
    for part in (0.5, 1.0):
        moved = N.new("GeometryNodeSetPosition")
        moved.name = f"Thick {part}"
        L.new(real.outputs[0], moved.inputs["Geometry"])
        L.new(vector("SCALE", unit.outputs[0], number("MULTIPLY", lacks, part)).outputs[0], moved.inputs["Offset"])
        sdf = N.new("GeometryNodeMeshToSDFGrid")
        L.new(moved.outputs[0], sdf.inputs["Mesh"])
        L.new(gi.outputs["Voxel"], sdf.inputs["Voxel Size"])
        sdf.inputs["Band Width"].default_value = band
        both = N.new("GeometryNodeSDFGridBoolean")
        both.operation = "UNION"
        for grid in (bones, sdf.outputs[0]):  # a union's grids all go into its one many-input socket
            L.new(grid, both.inputs["Grid 2"])
        bones = both.outputs[0]
    return bones


def rounded(group, middle):
    """The skull's Finish (the one cutting the Openings), once, thickened, sealed and rounded. Thickened: the vault's
    bones at least Thick through, inward toward `middle` (_thickened; the parietals are 0.8 to 2.2 mm thick at the
    temples, which the rounding took away: two holes, #874). Sealed: its bones' SDF grown by
    Seal, then eroded by it, before the shell and the cuts, so BodyParts3D's 21 bones, which only abut (the palate
    hung on one such gap, model/skeleton SEAL, #874), are one bone across every gap under twice Seal. Rounded: opened
    by Round before its Mean, eroded, then grown back, so every piece thinner than twice Round goes (#838's floor) and
    every convex edge, the orbits' and the nose's rims among them, comes out rounded to it (#993). Older scenes'
    Finishes get all three here, at export; build.py's are born with them."""
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
        sealed = _there_and_back(group, _thickened(group, bones, middle), "Seal", 1.0)
        for socket in into:
            L.new(sealed, socket)
    if "Round there" not in N and "Round erode" not in N:  # "Round erode": a scene saved by an older export
        mean = next(n for n in N if n.bl_idname == "GeometryNodeSDFGridMean")
        L.new(_there_and_back(group, mean.inputs["Grid"].links[0].from_socket, "Round", -1.0), mean.inputs["Grid"])


def capped(job):
    """Each capped skull's Finish (job["cap"]["of"]: the bare one's and the worn one's) cut along the seam, and its
    cap's made of it, a second Finished object on a copy of the group (#874, swap()'s Cap helpers). The Seats'
    bosses are united with the shelled bones before the openings and the carve, so the mechanism's room is cut from
    them as from any bone. The seam's cutter and each Seat's pocket (and, from the cap, its grooves) are cut from the
    mesh, exactly, before its crumbs are dropped: the grid chamfers every edge by a voxel, and left a magnet
    standing 0.7 mm proud on its pocket's floor. The group cuts what is above the skull's face, its copy what is
    below the cap's. Older scenes' Finishes get it here, at export, as rounded()'s."""
    for stem, cap in job["cap"]["of"].items():
        o = bpy.data.objects[f"finished {stem}"]
        group = o.modifiers["Finish"].node_group
        N, L = group.nodes, group.links
        if "Seam" not in N:
            node = next(
                n
                for n in N
                if n.bl_idname == "GeometryNodeCollectionInfo"
                and n.inputs["Collection"].default_value == bpy.data.collections[OPENINGS]
            )
            for _ in range(3):  # the Openings, realized, their grid, and the boolean that cuts them
                node = node.outputs[0].links[0].to_node
            shelled = node.inputs["Grid 1"]
            union = N.new("GeometryNodeSDFGridBoolean")
            union.operation = "UNION"
            for grid in (shelled.links[0].from_socket, _grid(group, _all(group, bpy.data.collections[BOSSES]))):
                L.new(grid, union.inputs["Grid 2"])  # a union's grids all go into its one many-input socket
            L.new(union.outputs[0], shelled)
            mesh = next(n for n in N if n.bl_idname == "GeometryNodeGridToMesh").outputs[0]
            readers = [link.to_socket for link in mesh.links]
            seam = N.new("GeometryNodeObjectInfo")
            seam.name, seam.transform_space = "Seam", "RELATIVE"
            cut = N.new("GeometryNodeMeshBoolean")
            cut.name, cut.operation, cut.solver = "Cut", "DIFFERENCE", "MANIFOLD"
            L.new(mesh, cut.inputs["Mesh 1"])
            for cutter in (seam.outputs["Geometry"], _all(group, bpy.data.collections[POCKETS])):
                L.new(cutter, cut.inputs["Mesh 2"])
            for socket in readers:
                L.new(cut.outputs["Mesh"], socket)
        twin = bpy.data.objects.get(f"finished {cap}")
        if not twin:
            twin = o.copy()
            twin.data = o.data.copy()  # its own mesh: the review bakes each Finish into its object's
            twin.name = twin.data.name = f"finished {cap}"
            for c in o.users_collection:
                c.objects.link(twin)
            twin.hide_set(o.hide_get())
            mine = twin.modifiers["Finish"].node_group = group.copy()
            mine.name = f"Finish {cap}"
            mine.links.new(_all(mine, bpy.data.collections[GROOVES]), mine.nodes["Cut"].inputs["Mesh 2"])
        for piece, cutter in zip((o, twin), SEAM, strict=True):  # swap() made the cutters anew
            piece.modifiers["Finish"].node_group.nodes["Seam"].inputs["Object"].default_value = bpy.data.objects[cutter]


def numbers(job):
    """The finish's numbers (model/skeleton: PITCH, CLEAR_MM, WALL, KEEP, the skull's Thick, Seal and Round) on
    every finish, the skull's cap's among them (capped())."""
    capped(job)
    middle = Vector(job["frame"]) + Vector(job["vault"]["middle"])  # the job's is in the head's frame
    for o in bpy.data.collections[FINISHED].objects:  # on the modifier: it keeps its own copy of each input
        mod = o.modifiers["Finish"]
        if mod.node_group:  # a Finish not wired yet (the review's stand-in scene) has nothing to round
            rounded(mod.node_group, o.matrix_world.inverted() @ middle)
        for key, value in job["numbers"].items():
            if key not in ("Thick", "Seal", "Round") or key in mod.node_group.interface.items_tree:  # the skull's
                getattr(mod.properties.inputs, mod.node_group.interface.items_tree[key].identifier).value = value


def _stl(path, me):
    """The mesh as a binary STL at `path`, triangulated (Blender's own exporter evaluates the whole scene again),
    without the folds the cap's exact cut leaves along the seam's edges (a dozen a piece): a sliver of the wall lying
    in the seam's plane, back to back with a sliver of its face on the same three points, 0.0005 mm2 each. Both go,
    and a reader that merges vertices finds every edge between two faces."""
    me.calc_loop_triangles()
    v = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", v)
    tri = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("vertices", tri)
    points = v.reshape(-1, 3)[tri.reshape(-1, 3)]
    order = np.lexsort((points[:, :, 2], points[:, :, 1], points[:, :, 0]))
    same = np.take_along_axis(points, order[:, :, None], axis=1).reshape(-1, 9)
    _, where, count = np.unique(same, axis=0, return_inverse=True, return_counts=True)
    points = points[count[where.ravel()] == 1]
    n = len(points)
    rec = np.zeros(n, [("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["v"] = points
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
