"""In Blender, once (#873): built model/skeleton/skeleton.blend, the Skeleton scene (docs/adr/0025), from the realistic
skull's bones as model/printed/skull.py placed them (in git's history), moved into the Stage 3 document's frame
unchanged. Since then the scene is the source: hand edits land in it, rewarp.py re-runs the warp, export.py finishes it.
Kept as the record of how its finishes are wired (and to wire a new bone's the same way).

  blender -b --factory-startup -P model/skeleton/build.py -- <build.json> <out.blend>

build.json: model/skeleton job() plus "placed" ({bone: its STL in the document's frame}).

The layers: Mech (the Scene Mech, CI's to replace), Skeleton (Skull: the bones, each with Basis, Warp and Sculpt shape
keys; Finished: a finish per exported bone, render and export only), helpers (hidden: Landmarks, Carve, Openings)."""

import json
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export  # noqa: E402

BUILD, OUT = sys.argv[sys.argv.index("--") + 1 :][:2]
JOB = json.load(open(BUILD))
BAND = 8  # the SDF's narrow band, voxels each side: past the shell's WALL, so the shrunk copy keeps its inside
MECH_RGBA, BONE_RGBA = (0.30, 0.32, 0.36, 1.0), (0.86, 0.80, 0.68, 1.0)


def material(name, rgba):
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgba
    return m


def finish_group(stem, bone):
    """The finish of `stem` (one of g.BONES) from the bone object `bone`, a Geometry Nodes SDF stack: the bone's SDF,
    shelled to Wall (the skulls), less the openings (the skulls), what rides it, what moves against it grown by the
    Clearance and a Skin's Shells grown by it (the worn copies), averaged once, meshed at its zero level, and every
    piece under Keep of the largest dropped (a worn copy: all but the largest, the piece inside the Shells)."""
    skull, worn = bone == "next skull", stem in JOB["worn"].values()
    g = bpy.data.node_groups.new(f"Finish {stem}", "GeometryNodeTree")
    g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    for name, value in JOB["numbers"].items():
        g.interface.new_socket(name, in_out="INPUT", socket_type="NodeSocketFloat").default_value = value
    N, L = g.nodes, g.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")

    def sdf(geo):
        m = N.new("GeometryNodeMeshToSDFGrid")
        L.new(geo, m.inputs["Mesh"])
        L.new(gi.outputs["Voxel"], m.inputs["Voxel Size"])
        m.inputs["Band Width"].default_value = BAND
        return m.outputs[0]

    def collection(c):
        n = N.new("GeometryNodeCollectionInfo")
        n.transform_space = "RELATIVE"
        n.inputs["Collection"].default_value = c
        n.inputs["Separate Children"].default_value = False
        r = N.new("GeometryNodeRealizeInstances")
        L.new(n.outputs[0], r.inputs[0])
        return r.outputs[0]

    def offset(grid, sock, sign=1.0):
        m = N.new("ShaderNodeMath")
        m.operation = "MULTIPLY"
        L.new(sock, m.inputs[0])
        m.inputs[1].default_value = sign
        o = N.new("GeometryNodeSDFGridOffset")
        L.new(grid, o.inputs["Grid"])
        L.new(m.outputs[0], o.inputs["Distance"])
        return o.outputs[0]

    def less(a, b):
        n = N.new("GeometryNodeSDFGridBoolean")
        n.operation = "DIFFERENCE"
        L.new(a, n.inputs["Grid 1"])
        L.new(b, n.inputs["Grid 2"])
        return n.outputs[0]

    o = N.new("GeometryNodeObjectInfo")
    o.transform_space = "RELATIVE"
    o.inputs["Object"].default_value = bpy.data.objects[bone]
    out = sdf(o.outputs["Geometry"])
    if skull:
        out = less(out, offset(out, gi.outputs["Wall"], -1.0))
        out = less(out, sdf(collection(bpy.data.collections[export.OPENINGS])))
    out = less(out, sdf(collection(export.carve(bone, "rigid"))))
    out = less(out, offset(sdf(collection(export.carve(bone, "moving"))), gi.outputs["Clearance"]))
    if worn:
        out = less(out, offset(sdf(collection(export.carve(bone, "skins"))), gi.outputs["Clearance"]))
    mean = N.new("GeometryNodeSDFGridMean")
    L.new(out, mean.inputs["Grid"])
    mesh = N.new("GeometryNodeGridToMesh")
    L.new(mean.outputs[0], mesh.inputs["Grid"])
    mesh.inputs["Threshold"].default_value = 0.0  # an SDF's surface (the node's default is a density's)
    # each piece's faces, against the largest piece's
    island = N.new("GeometryNodeInputMeshIsland")
    acc = N.new("GeometryNodeAccumulateField")
    acc.domain = "FACE"
    acc.inputs[0].default_value = 1.0
    L.new(island.outputs["Island Index"], acc.inputs["Group Index"])
    stat = N.new("GeometryNodeAttributeStatistic")
    stat.domain = "FACE"
    L.new(mesh.outputs[0], stat.inputs["Geometry"])
    L.new(acc.outputs["Total"], stat.inputs["Attribute"])
    keep = N.new("ShaderNodeMath")
    keep.operation = "MULTIPLY"
    L.new(stat.outputs["Max"], keep.inputs[0])
    if worn:
        keep.inputs[1].default_value = 0.999
    else:
        L.new(gi.outputs["Keep"], keep.inputs[1])
    small = N.new("FunctionNodeCompare")
    small.operation = "LESS_THAN"
    L.new(acc.outputs["Total"], small.inputs[0])
    L.new(keep.outputs[0], small.inputs[1])
    drop = N.new("GeometryNodeDeleteGeometry")
    drop.domain = "FACE"
    L.new(mesh.outputs[0], drop.inputs["Geometry"])
    L.new(small.outputs[0], drop.inputs["Selection"])
    st = N.new("GeometryNodeSetMaterial")
    st.inputs["Material"].default_value = bpy.data.materials["Bone"]
    L.new(drop.outputs[0], st.inputs["Geometry"])
    L.new(st.outputs[0], go.inputs[0])
    return g


# --- the scene: mm, empty
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
scene = bpy.context.scene
scene.unit_settings.scale_length, scene.unit_settings.length_unit = 0.001, "MILLIMETERS"
material("Bone", BONE_RGBA)
skeleton = export.collection("Skeleton")
skull = export.collection("Skull", skeleton)
finished = export.collection(export.FINISHED, skeleton)
helpers = export.collection("helpers")
landmarks = export.collection("Landmarks", helpers)

# --- the bones, unchanged, each with the warp's shape keys
lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
for bone, path in JOB["placed"].items():
    o = bpy.data.objects.new(bone, export._mesh(path))
    o.data.name = bone
    skull.objects.link(o)
    o.color = BONE_RGBA
    for key in ("Basis", "Warp", "Sculpt"):
        o.shape_key_add(name=key, from_mix=False)
    keys = o.data.shape_keys.key_blocks
    keys["Sculpt"].relative_key = keys["Warp"]
    keys["Warp"].value = keys["Sculpt"].value = 1.0
    for v in o.data.vertices:
        lo, hi = Vector(map(min, lo, v.co, strict=True)), Vector(map(max, hi, v.co, strict=True))
# the warp's fixed frame: a landmark at each corner of the bones' box, 20 mm out, its own target (rewarp.py: no move)
for i, c in enumerate(
    (x, y, z) for x in (lo.x - 20, hi.x + 20) for y in (lo.y - 20, hi.y + 20) for z in (lo.z - 20, hi.z + 20)
):
    e = bpy.data.objects.new(f"LM frame {i}", None)
    e.location, e.empty_display_size = c, 3.0
    landmarks.objects.link(e)

# --- the Scene Mech and the carve sets, light, then a finish per exported bone
export.swap(JOB, ratio=0.1)
for o in export.collection(export.MECH).objects:
    o.color = MECH_RGBA
sources = {s: s for s in JOB["placed"]} | {w: b for b, w in JOB["worn"].items()}
for stem, bone in sources.items():
    o = bpy.data.objects.new(f"finished {stem}", bpy.data.meshes.new(f"finished {stem}"))
    finished.objects.link(o)
    o.hide_set(stem in JOB["worn"].values())  # the worn copies: what a Skin wears, hidden bare
    mod = o.modifiers.new("Finish", "NODES")
    mod.node_group = finish_group(stem, bone)
    mod.show_viewport = False  # the slow finish: render and export only (export.py turns it on)
skull.hide_render = True  # the finished bones render, the raw ones are worked on
bpy.context.view_layer.layer_collection.children[helpers.name].hide_viewport = True
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT), compress=True)
print("build: done", flush=True)
