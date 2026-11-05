"""Seam: the review file as model/review writes it (#915): light checks of its plan (the loop, the plates, the lock),
and the written .blend itself read by headless Blender, locally once `just review` wrote it (NOGGIN_REVIEW names it:
the recipe runs this file after each build)."""

import json
import os
import shutil

import pytest

from model import geometry as g
from model import review, stages

STAGE = stages.STAGES[review.DOC]


def test_the_loop_takes_every_horn_to_each_end_of_its_range_and_back_to_rest():
    """Each horn's keys reach its limits, its servo's range (ADR 0011), and are 0 on the loop's first and last frame."""
    for horn, pts in review.keys(STAGE).items():
        degs = [d for _, d in pts]
        assert (min(degs), max(degs)) == pytest.approx(STAGE.horns[horn].limits), horn
        assert pts[0] == (1, 0.0) and pts[-1] == (review.FRAMES, 0.0)


def test_the_bones_ride_their_regions():
    """The skull and mandible in Skull, the atlas and axis in Mechanism, the Torso in Pedestal."""
    region = review.regions()
    assert region["worn skull:1"] == region["worn mandible:1"] == "Skull"
    assert region["atlas:1"] == region["axis:1"] == "Mechanism"
    assert region["torso:1"] == "Pedestal"


def test_pack_keeps_every_piece_on_a_plate_clear_of_its_edge():
    """Each footprint inside its plate, GAP from the edge; a new plate once one is full; too big a piece refused."""
    sizes = [(120, 100), (200, 60), (90, 90), (240, 30), (100, 120), (50, 50)] * 3
    for (w, d), (_, x, y) in zip(sizes, review.pack(sizes), strict=True):
        assert review.GAP <= x and x + w <= review.BED - review.GAP
        assert review.GAP <= y and y + d <= review.BED - review.GAP
    assert len({p for p, _, _ in review.pack(sizes)}) > 1
    with pytest.raises(ValueError):
        review.pack([(review.BED, 10)])


def test_a_second_writer_is_refused_while_the_lock_is_held(tmp_path):
    path = str(tmp_path / "review.blend.lock")
    held = review.lock(path)
    with pytest.raises(SystemExit, match="another writer"):
        review.lock(path)
    held.close()
    review.lock(path).close()


REFERENCE_CARRIERS = {
    role: stages.RIDES[shell]
    for role, shell in {
        "head": "morty face:1",
        "jaw": "morty mouth cover:1",
        "L eye": "morty L pupil:1",
        "R eye": "morty R pupil:1",
    }.items()
}

INSPECT = (
    f"EXPECTED_REFERENCE = {REFERENCE_CARRIERS!r}\n"
    + """
import json, bpy, numpy as np
def walk(lc):
    yield lc
    for c in lc.children:
        yield from walk(c)
a = bpy.data.scenes["Assembled"]
a.frame_set(a.frame_start)
out = {"scenes": [s.name for s in bpy.data.scenes], "first": bpy.context.window_manager.windows[0].scene.name}
out["layers"] = {c.name: {k.name: sorted({round(o.color[3], 2) for o in k.objects}) for k in c.children}
                 for c in bpy.data.collections if c.name in ("Mech", "Skeleton", "Morty")}
out["layer_material_alpha"] = {c.name: sorted({round(slot.material.diffuse_color[3], 2)
    for o in c.all_objects for slot in o.material_slots if slot.material})
    for c in bpy.data.collections if c.name in ("Mech", "Skeleton", "Morty")}
out["morty"] = len(bpy.data.collections["Morty"].all_objects)
out["shading"] = a.display.shading.color_type
out["skin"] = {o.data.materials[p.material_index].name: list(o.data.materials[p.material_index].diffuse_color)
               for o in bpy.data.collections["Morty"].all_objects for p in o.data.polygons
               if o.data.materials}
base = [o.matrix_world @ v.co for o in bpy.data.collections["Mech Pedestal"].objects for v in o.data.vertices]
out["floor"] = min((v.z for v in base), default=None)
bust = [o.matrix_world @ v.co for o in bpy.data.collections["Morty Pedestal"].objects for v in o.data.vertices]
caps = sum(all(abs((o.matrix_world @ o.data.vertices[i].co).z - out["floor"]) < 0.01 for i in p.vertices)
    for o in bpy.data.collections["Morty Pedestal"].objects for p in o.data.polygons) if base else 0
out["bust"] = [min(v.z for v in bust), caps] if bust and base else None
out["material_alpha"] = {s.name: sorted({round(slot.material.diffuse_color[3], 2)
    for o in s.objects if o.type == "MESH" and not o.name.startswith("Plate")
    for slot in o.material_slots if slot.material}) for s in bpy.data.scenes if s.name in ("Exploded", "Print bed")}
out["helpers"] = next(l.hide_viewport for l in walk(a.view_layers[0].layer_collection) if l.name == "helpers")
horns = [o for o in bpy.data.objects if o.name.startswith("horn ")]
out["actions"] = sorted({o.animation_data.action.name for o in a.objects if o.animation_data})
deg = {o.name[5:]: [] for o in horns}
reference = {}
reference_witnesses = []
out["reference_witnesses"] = {}
for o in bpy.data.collections["Morty"].all_objects:
    if o.get("reference_region"):
        v = np.empty(len(o.data.vertices) * 3)
        o.data.vertices.foreach_get("co", v)
        v = v.reshape(-1, 3)
        m = np.array(o.matrix_world)
        reference[o.name] = (o, v, v @ m[:3, :3].T + m[:3, 3])
        for g in o.vertex_groups:
            if g.name in ("witness neck", "witness L shoulder", "witness R shoulder"):
                indices = [p.index for p in o.data.vertices if any(x.group == g.index and x.weight > .5 for x in p.groups)]
                points = v[indices]
                reference_witnesses.append((g.name, o, points, points @ m[:3, :3].T + m[:3, 3]))
                out["reference_witnesses"].setdefault(g.name, []).append({"region": o["reference_region"],
                    "vertices": len(points), "travel": 0.0})
actors = {o["part"]: o for o in a.objects if o.get("part")}
actor_rest = {role: np.array(actors[part].matrix_world) for role, part in EXPECTED_REFERENCE.items() if part in actors}
actor_back = {role: np.linalg.inv(m) for role, m in actor_rest.items()}
out["reference_motion"] = {o["reference_region"]: {"vertices": len(v), "travel": 0.0,
    "carrier_error": None, "own_travel": 0.0}
    for o, v, rest in reference.values()}
for f in range(a.frame_start, a.frame_end + 2):
    a.frame_set(f)
    for o in horns:
        deg[o.name[5:]].append(o["deg"])
    for o, v, rest in reference.values():
        m = np.array(o.matrix_world)
        travel = np.linalg.norm(v @ m[:3, :3].T + m[:3, 3] - rest, axis=1).max()
        region = out["reference_motion"][o["reference_region"]]
        region["travel"] = max(region["travel"], float(travel))
        role = o["reference_region"]
        if role in actor_back and "head" in actor_back:
            delta = np.array(actors[EXPECTED_REFERENCE[role]].matrix_world) @ actor_back[role]
            now = v @ m[:3, :3].T + m[:3, 3]
            expected = rest @ delta[:3, :3].T + delta[:3, 3]
            error = float(np.linalg.norm(now - expected, axis=1).max())
            region["carrier_error"] = max(region["carrier_error"] or 0.0, error)
            head_back = np.linalg.inv(np.array(actors[EXPECTED_REFERENCE["head"]].matrix_world))
            local_now = now @ head_back[:3, :3].T + head_back[:3, 3]
            local_rest = rest @ actor_back["head"][:3, :3].T + actor_back["head"][:3, 3]
            region["own_travel"] = max(region["own_travel"], float(np.linalg.norm(local_now - local_rest, axis=1).max()))
    for name, o, v, rest in reference_witnesses:
        m = np.array(o.matrix_world)
        travel = float(np.linalg.norm(v @ m[:3, :3].T + m[:3, 3] - rest, axis=1).max()) if len(v) else 0.0
        witness = next(w for w in out["reference_witnesses"][name] if w["region"] == o["reference_region"])
        witness["travel"] = max(witness["travel"], travel)
out["horns"] = {h: [min(v), max(v), v[0], v[-1]] for h, v in deg.items()}
mech_layer = a.view_layers[0].layer_collection.children["Mech"]
hidden = mech_layer.hide_viewport
mech_layer.hide_viewport = True
a.frame_set(156)
out["reference_visible_without_mech"] = all(o.visible_get(view_layer=a.view_layers[0]) for o, _, _ in reference.values())
mech_layer.hide_viewport = hidden
bed, out["plates"] = bpy.data.scenes["Print bed"], {}
for c in bed.collection.children:
    plate = next(o for o in c.objects if o.name.startswith("Plate"))
    x0 = min((plate.matrix_basis @ v.co).x for v in plate.data.vertices)
    lo = hi = None
    for o in c.objects:
        if o is not plate:
            for v in o.data.vertices:
                p = o.matrix_basis @ v.co  # no parents; a scene never shown keeps a stale matrix_world
                lo = [min(a, b) for a, b in zip(lo or p, p)]
                hi = [max(a, b) for a, b in zip(hi or p, p)]
    out["plates"][c.name] = [lo[0] - x0, lo[1], lo[2], hi[0] - x0, hi[1], len(c.objects) - 1]
print("INSPECT " + json.dumps(out))
print("review: done")
"""
)


@pytest.fixture(scope="module")
def blend():
    path = os.environ.get("NOGGIN_REVIEW")
    if not path or not os.path.isfile(path):
        pytest.skip("no review file to read (NOGGIN_REVIEW: just review sets it)")
    held = review.lock(review.SLOT, wait=True)
    try:
        log = review._blender([path, "--python-expr", INSPECT])
    finally:
        held.close()
    line = next(x for x in log.splitlines() if x.startswith("INSPECT "))
    return json.loads(line.removeprefix("INSPECT "))


def test_the_file_opens_on_assembled_beside_exploded_and_print_bed(blend):
    assert blend["first"] == blend["scenes"][0] == "Assembled"
    assert {"Exploded", "Print bed"} <= set(blend["scenes"])


def test_each_layer_has_its_regions_at_its_alpha_and_helpers_are_hidden(blend):
    """Mech, Skeleton and Morty, each in Skull, Mechanism and Pedestal, every object at the layer's alpha; Morty's
    objects only with the local reference (a fresh clone builds without them)."""
    for layer, alpha in review.ALPHA.items():
        regions = blend["layers"][layer]
        assert sorted(regions) == sorted(f"{layer} {r}" for r in ("Skull", "Mechanism", "Pedestal"))
        assert all(a in ([], [alpha]) for a in regions.values()), (layer, regions)
        assert blend["layer_material_alpha"][layer] in ([], [alpha])
    assert bool(blend["morty"]) == os.path.isfile(review.MORTY)
    assert blend["helpers"]
    assert blend["reference_visible_without_mech"]


def test_one_looping_action_sweeps_each_horn_over_its_servos_range(blend):
    assert blend["actions"] == ["Review motion"]
    for horn, (lo, hi, first, last) in blend["horns"].items():
        assert (lo, hi) == pytest.approx(STAGE.horns[horn].limits, abs=1e-4), horn
        assert first == last == 0.0


def test_mortys_sections_show_the_default_skin_palette_at_33_percent(blend):
    if not blend["morty"]:
        pytest.skip("no local Morty reference")
    assert blend["shading"] == "MATERIAL"
    groups = {"face", "hair", "pupils", "clothes", "eye whites"}
    assert set(blend["skin"]) == groups
    for group, rgba in blend["skin"].items():
        hex_ = g.THEMES["Skin palette"]["default"][group][3]
        srgb = [int(hex_[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
        assert rgba == pytest.approx([*linear, 0.33])


def test_the_reference_neck_shoulders_and_torso_stay_fixed_while_the_head_moves(blend):
    if not blend["morty"]:
        pytest.skip("no local Morty reference")
    motion = blend["reference_motion"]
    assert {"neck", "shoulders", "torso", "head"} <= motion.keys()
    for name in ("neck", "shoulders", "torso"):
        assert motion[name]["vertices"] >= 3
        assert motion[name]["travel"] == pytest.approx(0.0, abs=1e-3), name
    assert motion["head"]["travel"] > 1.0
    for name, role in {"neck": "neck", "L shoulder": "shoulders", "R shoulder": "shoulders"}.items():
        witnesses = blend["reference_witnesses"]["witness " + name]
        assert all(w["region"] == role and w["vertices"] > 0 for w in witnesses), name
        assert all(w["travel"] < 1e-3 for w in witnesses), name


def test_mortys_bust_stops_at_the_models_flat_floor(blend):
    if not blend["morty"]:
        pytest.skip("no local Morty reference")
    low, caps = blend["bust"]
    assert low == pytest.approx(blend["floor"], abs=0.01)
    assert caps > 0


def test_the_reference_jaw_and_eyes_follow_their_live_carriers_independently_of_the_head(blend):
    if not blend["morty"]:
        pytest.skip("no local Morty reference")
    motion = blend["reference_motion"]
    for role in REFERENCE_CARRIERS:
        assert motion[role]["vertices"] > 0
        assert motion[role]["carrier_error"] is not None, role
        assert motion[role]["carrier_error"] < 1e-3, role
    assert motion["head"]["own_travel"] < 1e-3
    assert all(motion[role]["own_travel"] > 1.0 for role in ("jaw", "L eye", "R eye"))


def test_exploded_and_print_bed_materials_are_opaque(blend):
    assert blend["material_alpha"] == {"Exploded": [1.0], "Print bed": [1.0]}


def test_every_printed_piece_lies_on_a_plate(blend):
    """Each plate's pieces inside its BED square, on it (z 0 and up); every printed part placed once."""
    n = 0
    for plate, (x0, y0, z0, x1, y1, count) in blend["plates"].items():
        assert -0.5 <= x0 and x1 <= review.BED + 0.5 and -0.5 <= y0 and y1 <= review.BED + 0.5, plate
        assert z0 >= -0.5, plate
        n += count
    assert n == len(review.plates(STAGE))


NORMAL_REFERENCE = """
import bpy, json, math, runpy, sys
from pathlib import Path
from mathutils import Matrix, Vector
folder=Path(FOLDER)
identity=Matrix.Identity(4)
at=Matrix.Diagonal((7.13, 3.17 if NONUNIFORM else 7.13, 7.13, 1.0))
if NONUNIFORM: at=Matrix.Rotation(.4, 4, 'Z') @ at
at.translation=(-1200,5000,-600)
normal=Vector((0,-.3,math.sqrt(.91)))
reference=bpy.data.collections.new('Morty reference')
for role in ('head','neck','shoulders','torso'):
    if role=='head':
        mesh=bpy.data.meshes.new(role)
        mesh.from_pydata([(100,200,300),(101,200,300),(100.5,200.00002,300.00003)],[],[(0,1,2)])
        mesh.polygons[0].use_smooth=True
        for edge in mesh.edges: edge.use_edge_sharp=True
        mesh.normals_split_custom_set([normal]*3)
        mesh.attributes.new('authored face','INT','FACE').data[0].value=17
    else:
        bpy.ops.mesh.primitive_cube_add(size=1,location=(100,200,300 if role=='torso' else 302))
        cube=bpy.context.object
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
        mesh=cube.data.copy()
        bpy.data.objects.remove(cube,do_unlink=True)
    material=bpy.data.materials.get('clothes' if role=='torso' else 'face')
    material=material or bpy.data.materials.new('clothes' if role=='torso' else 'face')
    mesh.materials.append(material)
    obj=bpy.data.objects.new(role,mesh)
    obj['reference_region']=role
    obj['display_region']='Pedestal' if role=='torso' else 'Mechanism' if role=='neck' else 'Skull'
    if role=='head': obj['carrier']='carrier:1'
    for witness in {'neck':['witness neck'],'shoulders':['witness L shoulder','witness R shoulder']}.get(role,[]):
        obj.vertex_groups.new(name=witness).add([0],1,'REPLACE')
    reference.objects.link(obj)
source=folder/'reference.blend'
bpy.data.libraries.write(str(source),{reference},compress=True)
for obj in list(reference.objects): bpy.data.objects.remove(obj,do_unlink=True)
bpy.data.collections.remove(reference)
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.mesh.primitive_cube_add(size=1)
cube=bpy.context.object
bpy.ops.wm.stl_export(filepath=str(folder/'marker.stl'),export_selected_objects=True)
cube.name='finished worn skull'
cube.modifiers.new('Finish','NODES')
top=bpy.data.collections.new('Skeleton')
bpy.context.scene.collection.children.link(top)
for name in ('Skull','Finished'):
    collection=bpy.data.collections.new(name)
    top.children.link(collection)
for collection in list(cube.users_collection): collection.objects.unlink(cube)
bpy.data.collections['Finished'].objects.link(cube)
job={'files':{'carrier:1':str(folder/'marker.stl')},'bones':{},'frame':[0,0,0],
     'rest':{'carrier:1':list(identity)},'orbits':[],'reach':0,'numbers':{},
     'parts':{'carrier:1':{'region':'Skull','layer':'Mech','colour':'#FFFFFF'},
              'worn skull:1':{'region':'Skull','layer':'Skeleton','colour':'#FFFFFF'}},
     'alpha':{'Mech':1,'Skeleton':.69,'Morty':.33},
     'motion':[[1,{'carrier:1':list(identity)}]],
     'morty':{'blend':str(source),'at':list(at),'floor':1538,
              'colours':{'face':'#F7CED7','clothes':'#FFFFFF'}}}
job_path=folder/'job.json'
job_path.write_text(json.dumps(job,default=list))
output=folder/'review.blend'
sys.argv=['blender','--',str(job_path),str(output),'assemble']
runpy.run_path(SCRIPT,run_name='__main__')
bpy.ops.wm.open_mainfile(filepath=str(output),load_ui=False)
head=next(o for o in bpy.data.objects if o.get('reference_region')=='head')
torso=next(o for o in bpy.data.objects if o.get('reference_region')=='torso')
expected=(at.to_3x3().inverted().transposed() @ normal).normalized()
result={'normal_dot':min(n.vector.dot(expected) for n in head.data.corner_normals),
        'finite':all(math.isfinite(c) for v in head.data.vertices for c in v.co),
        'vertices':len(head.data.vertices),'faces':[list(p.vertices) for p in head.data.polygons],
        'attribute':head.data.attributes['authored face'].data[0].value,
        'material':head.data.materials[head.data.polygons[0].material_index].name,
        'custom_normals':head.data.has_custom_normals,
        'ordinary_profile_custom_normals':torso.data.has_custom_normals,
        'floor':min(v.co.z for v in torso.data.vertices),
        'caps':sum(all(abs(torso.data.vertices[i].co.z-1538)<.001 for i in p.vertices)
                   for p in torso.data.polygons)}
print('NORMALS '+json.dumps(result),flush=True)
print('review: done',flush=True)
"""


@pytest.mark.bones
@pytest.mark.parametrize("nonuniform", [False, True])
def test_saved_reference_preserves_authored_normals_and_still_cuts_the_floor(tmp_path, nonuniform):
    """A public thin triangle with authored normals; no private reference or generated model parts needed."""
    if not shutil.which(review.skeleton.BLENDER):
        pytest.skip(f"no Blender found at {review.skeleton.BLENDER}")
    prefix = f"FOLDER={str(tmp_path)!r}\nSCRIPT={review.SCRIPT!r}\nNONUNIFORM={nonuniform!r}\n"
    script = tmp_path / "reference.py"
    script.write_text(prefix + NORMAL_REFERENCE)
    held = review.lock(review.SLOT, wait=True)
    try:
        log = review._blender(["--python-exit-code", "1", "-P", str(script)])
    finally:
        held.close()
    actual = json.loads(next(line.removeprefix("NORMALS ") for line in log.splitlines() if line.startswith("NORMALS ")))
    assert actual["normal_dot"] > 0.9999
    assert actual["finite"] and actual["vertices"] == 3 and actual["faces"] == [[0, 1, 2]]
    assert actual["attribute"] == 17 and actual["material"] == "face" and actual["custom_normals"]
    assert not actual["ordinary_profile_custom_normals"]
    assert actual["floor"] == pytest.approx(1538, abs=0.001) and actual["caps"] > 0
