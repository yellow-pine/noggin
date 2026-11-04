"""One-time BodyParts3D scene adapter: retain raw keys/live SDF finishes; replace prototype cutters and output names.

In Blender: source.blend -P adopt.py -- <job.json> <out.blend>. The canonical output registry comes in the job;
no anatomical mesh is built here. `refresh` also updates the teaching joint after an authored rewarp.
"""

import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
import export  # noqa: E402


def upstream(socket):
    nodes, pending = set(), [link.from_node for link in socket.links]
    while pending:
        node = pending.pop()
        if node not in nodes:
            nodes.add(node)
            pending.extend(link.from_node for pin in node.inputs for link in pin.links)
    return nodes


def collection_geometry(group, collection):
    node = group.nodes.new("GeometryNodeCollectionInfo")
    node.transform_space = "RELATIVE"
    node.inputs["Collection"].default_value = collection
    node.inputs["Separate Children"].default_value = False
    realize = group.nodes.new("GeometryNodeRealizeInstances")
    group.links.new(node.outputs[0], realize.inputs[0])
    return realize.outputs[0]


def grid(group, collection):
    node = group.nodes.new("GeometryNodeMeshToSDFGrid")
    group.links.new(collection_geometry(group, collection), node.inputs["Mesh"])
    group.links.new(
        next(n for n in group.nodes if n.bl_idname == "NodeGroupInput").outputs["Voxel"], node.inputs["Voxel Size"]
    )
    node.inputs["Band Width"].default_value = 8
    return node.outputs[0]


def wire(group, bone, definition, worn, job):
    """Keep the authored thickening/teaching cut; fresh rigid/moving/Skin sets replace the prototype's global carve."""
    gi = next(n for n in group.nodes if n.bl_idname == "NodeGroupInput")
    for node in list(group.nodes):
        if node.bl_idname != "GeometryNodeSDFGridBoolean" or node.operation != "INTERSECT":
            continue
        inputs = [link.from_socket for pin in node.inputs for link in pin.links]
        missing = []
        for pin in inputs:
            parents = upstream(pin)
            if not any(n.bl_idname == "GeometryNodeCollectionInfo" for n in parents) and any(
                n.bl_idname == "GeometryNodeObjectInfo" and n.inputs["Object"].default_value is None for n in parents
            ):
                missing.append(pin)
        if missing:
            remaining = [pin for pin in inputs if pin not in missing]
            assert len(remaining) == 1, "Ambiguous private-limit intersection"
            for link in list(node.outputs[0].links):
                group.links.new(remaining[0], link.to_socket)
            group.nodes.remove(node)  # the deliberately absent private Morph is never an empty-volume clip
    carve = next(
        n
        for n in group.nodes
        if n.get("bone_carve")
        or (
            n.bl_idname == "GeometryNodeSDFGridBoolean"
            and n.operation == "DIFFERENCE"
            and any(
                x.bl_idname == "GeometryNodeCollectionInfo"
                and x.inputs["Collection"].default_value.name.startswith("Carve")
                for x in upstream(n.inputs["Grid 2"])
            )
        )
    )
    if not carve.get("bone_carve"):
        carve["bone_carve"] = True
        carve["targets"] = json.dumps([(l.to_node.name, l.to_socket.identifier) for l in carve.outputs[0].links])
    cuts = []
    for kind in ("rigid", "moving", *(("skins",) if worn else ())):
        if not export.carve(bone, kind).all_objects:
            continue
        parts = (
            sorted(
                n
                for n in {n for n, _ in job["bones"].get(bone, {}).get(kind, [])}
                if export.carve(bone, kind, n).all_objects
            )
            if kind == "moving"
            else []
        )
        if kind == "moving":
            assert sum(len(export.carve(bone, kind, n).all_objects) for n in parts) == len(
                export.carve(bone, kind).all_objects
            ), "Every spatially retained cutter pose must reach the SDF union"
        inputs = [grid(group, export.carve(bone, kind, n)) for n in parts] or [grid(group, export.carve(bone, kind))]
        if len(inputs) > 1:
            sweep = group.nodes.new("GeometryNodeSDFGridBoolean")
            sweep.operation = "UNION"
            pin = next(s for s in sweep.inputs if s.enabled and s.is_multi_input)
            for value in inputs:
                group.links.new(value, pin)
            cut = sweep.outputs[0]
        else:
            cut = inputs[0]
        if kind != "rigid":
            offset = group.nodes.new("GeometryNodeSDFGridOffset")
            group.links.new(cut, offset.inputs["Grid"])
            group.links.new(gi.outputs["Clearance"], offset.inputs["Distance"])
            cut = offset.outputs[0]
        cuts.append(cut)
    if definition["source"] == "Skull":
        cuts.append(grid(group, export.collection(export.OPENINGS, export.collection("helpers"))))
    # Blender 5's SDF Boolean Grid 2 accepts multiple links. Replacing it must
    # remove the prototype cutter, otherwise both old and current Mech are cut
    # (and both large SDF branches are evaluated).
    for link in list(carve.inputs["Grid 2"].links):
        group.links.remove(link)
    if cuts:
        union = group.nodes.new("GeometryNodeSDFGridBoolean")
        union.operation = "UNION"
        socket = next(s for s in union.inputs if s.enabled and s.is_multi_input)
        for cut in cuts:
            group.links.new(cut, socket)
        group.links.new(union.outputs[0], carve.inputs["Grid 2"])
        assert [link.from_node for link in carve.inputs["Grid 2"].links] == [union]
        result = carve.outputs[0]
    else:
        # Blender 5.2's SDF Boolean treats an empty operand as invalid, rather
        # than an identity. A Bone that meets no cutters keeps its source.
        result = carve.inputs["Grid 1"].links[0].from_socket
    for name, identifier in json.loads(carve["targets"]):
        target = next(s for s in group.nodes[name].inputs if s.identifier == identifier)
        for link in list(target.links):
            group.links.remove(link)
        group.links.new(result, target)
    assert not any(
        n.bl_idname == "GeometryNodeCollectionInfo" and n.inputs["Collection"].default_value.name.startswith("Carve (")
        for n in upstream(carve.inputs["Grid 2"])
    ), "The prototype Mech must not survive the current per-Bone carve"
    if definition["source"] == "Skull":
        raw = next(
            n
            for n in group.nodes
            if n.bl_idname == "GeometryNodeMeshToSDFGrid"
            and any(
                x.bl_idname == "GeometryNodeCollectionInfo" and x.inputs["Collection"].default_value.name == "Skull"
                for x in upstream(n.inputs["Mesh"])
            )
        )
        if not any(
            x.bl_idname == "GeometryNodeCollectionInfo"
            and x.inputs["Collection"].default_value.name == "Calvaria joints"
            for x in upstream(raw.inputs["Mesh"])
        ):
            join = group.nodes.new("GeometryNodeJoinGeometry")
            group.links.new(raw.inputs["Mesh"].links[0].from_socket, join.inputs[0])
            group.links.new(
                collection_geometry(group, export.collection("Calvaria joints", export.collection("helpers"))),
                join.inputs[0],
            )
            group.links.new(join.outputs[0], raw.inputs["Mesh"])
    output = next(n for n in group.nodes if n.bl_idname == "NodeGroupOutput")
    used = upstream(output.inputs[0]) | {output, carve} | upstream(carve.inputs["Grid 1"])
    for node in list(group.nodes):
        if node not in used:
            group.nodes.remove(node)
    inset = group.interface.items_tree.get("Inset")
    if inset:
        group.interface.remove(inset)


def cylinder(name, radius, depth, at, collection):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=radius, radius2=radius, depth=depth)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    o.location, o.hide_render, o.display_type = at, True, "WIRE"
    collection.objects.link(o)


def refresh():
    """Three integral bosses/pockets on the actual warped cut ring; their outer extent stays inside its growth budget."""
    numbers = json.loads(bpy.context.scene["bone_finish_numbers"])
    wall, seam = 2 * (numbers["Grow"] - numbers["Shrink"]), 0.4
    cut_z = bpy.data.objects["LM glabella target"].matrix_world.translation.z + 12
    cut = bpy.data.objects["Calvaria cut"]
    old_z = min((cut.matrix_world @ Vector(p)).z for p in cut.bound_box)
    cut.matrix_world = Matrix.Translation((0, 0, cut_z - old_z)) @ cut.matrix_world
    bosses = export.collection("Calvaria joints", export.collection("helpers"))
    pockets = export.collection("Magnet pockets", export.collection("helpers"))
    export._empty(bosses)
    export._empty(pockets)
    vertices, faces = [], []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in bpy.data.collections["Skull"].all_objects:
        if o.type != "MESH":
            continue
        evaluated = o.evaluated_get(dg)
        mesh = evaluated.to_mesh()
        offset = len(vertices)
        vertices.extend(o.matrix_world @ v.co for v in mesh.vertices)
        faces.extend([offset + i for i in p.vertices] for p in mesh.polygons)
        evaluated.to_mesh_clear()
    tree, origin = BVHTree.FromPolygons(vertices, faces), Vector((0, -75, cut_z))
    # Six is the authored source SDF band. Include every filter iteration,
    # offset and moving clearance as additional support, rather than reducing
    # the final voxel/wall/clearance settings to fit the resource limit.
    margin = (6 + numbers["Fillet"] + 2) * numbers["Voxel"] + numbers["Grow"] + numbers["Shrink"] + numbers["Clearance"]
    for label, angle in (("front", -90), ("back L", 45), ("back R", 135)):
        d = Vector((math.cos(math.radians(angle)), math.sin(math.radians(angle)), 0))
        at, cursor = None, origin
        for _ in range(32):
            hit = tree.ray_cast(cursor, d, 500)[0]
            if hit is None:
                break
            at, cursor = hit, hit + d * 0.001
        assert at is not None, f"No calvaria cut-ring cortex at {label}"
        radius, depth = 2.0 + 0.1, 2 * (2.0 + 0.1) + seam  # the prototype's 4×2 magnets, 0.1 mm play
        centre = at - d * (radius + wall)
        cylinder("calvaria joint " + label, radius + wall, depth + 2 * wall, centre, bosses)
        cylinder("calvaria pocket " + label, radius, depth, centre, pockets)
    bpy.context.view_layer.update()
    domain = vertices + [o.matrix_world @ v.co for o in bosses.objects for v in o.data.vertices]
    lo = [min(v[i] for v in domain) - margin for i in range(3)]
    hi = [max(v[i] for v in domain) + margin for i in range(3)]
    # The prototype's 500×600×400 mm half-space stand-in needlessly voxelizes
    # its remote five faces. Recompute from the current warped/Sculpted source
    # and bosses on every rewarp. Only the teaching plane meets that domain.
    lo[2] = cut_z
    bounded = export._box("bounded teaching cut", lo, hi, export.collection("helpers"))
    cut.data = bounded.data
    cut.matrix_world = Matrix.Identity(4)
    bpy.data.objects.remove(bounded)
    cut["support_margin_mm"] = margin
    assert abs(min(v.co.z for v in cut.data.vertices) - cut_z) < 1e-4
    for i in range(3):
        assert max(v.co[i] for v in cut.data.vertices) >= max(v[i] for v in domain) + margin - 1e-4
        if i != 2:
            assert min(v.co[i] for v in cut.data.vertices) <= min(v[i] for v in domain) - margin + 1e-4


def adopt(job):
    assert "bone_parts" not in bpy.context.scene, "Already adopted; edit its keys and use just rewarp"
    parts = job["parts"]
    finished = bpy.data.collections.get("Finished (render only)") or export.collection(export.FINISHED)
    finished.name = export.FINISHED
    export.swap(job, ratio=0.1)
    aliases = {"calvaria": "Calvaria", "skull": "Face and skull base", "mandible": "Mandible"}
    for bone, definition in parts.items():
        o = bpy.data.objects.get("finished " + bone) or bpy.data.objects["finished " + aliases.get(bone, bone.upper())]
        o.name = "finished " + bone
        wire(o.modifiers["Finish"].node_group, bone, definition, False, job)
    for bone, stem in job["worn"].items():
        bare = bpy.data.objects["finished " + bone]
        o = bare.copy()
        o.name = "finished " + stem
        o.modifiers["Finish"].node_group = bare.modifiers["Finish"].node_group.copy()
        finished.objects.link(o)
        wire(o.modifiers["Finish"].node_group, bone, parts[bone], True, job)
    desired = set(parts) | set(job["worn"].values())
    for o in list(finished.objects):
        if o.name.removeprefix("finished ") not in desired:
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        o.data = bpy.data.meshes.new(o.name)  # the source keeps its live finish, never stale baked output
        for mod in o.modifiers:
            mod.show_viewport = mod.show_render = False
        bone = next(
            (b for b, w in job["worn"].items() if w == o.name.removeprefix("finished ")),
            o.name.removeprefix("finished "),
        )
        if parts[bone]["source"] == "Skull":
            cut = o.modifiers.new("Magnet pockets", "BOOLEAN")
            cut.operation, cut.operand_type, cut.solver = "DIFFERENCE", "COLLECTION", "EXACT"
            cut.collection = export.collection("Magnet pockets", export.collection("helpers"))
            cut.show_viewport = cut.show_render = False
    bpy.context.scene["bone_parts"] = json.dumps(parts)
    bpy.context.scene["bone_finish_numbers"] = json.dumps(job["numbers"])
    export.numbers(job)
    refresh()
    if "rewarp.py" in bpy.data.texts:
        bpy.data.texts.remove(bpy.data.texts["rewarp.py"])
    note = bpy.data.texts.get("Warp workflow") or bpy.data.texts.new("Warp workflow")
    note.clear()
    note.write(
        "Save this source, then run just rewarp in its worktree. Public Bone data goes to GX10; private Morph stays local.\n"
    )
    if "Mech changes" in bpy.data.texts:
        history = bpy.data.texts["Mech changes"]
        old = history.as_string()
        history.clear()
        history.write("HISTORICAL prototype 8a937251; not the current electronics or accepted mechanism.\n" + old)


if __name__ == "__main__":
    job_path, out = sys.argv[sys.argv.index("--") + 1 :]
    adopt(json.load(open(job_path)))
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out), compress=True)
    print("review: done", flush=True)
