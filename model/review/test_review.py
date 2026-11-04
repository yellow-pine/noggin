"""Seam: the review file as model/review writes it (#915): light checks of its plan (the loop, the plates, the lock),
and the written .blend itself read by headless Blender, locally once `just review` wrote it (NOGGIN_REVIEW names it:
the recipe runs this file after each build)."""

import json
import os
import subprocess

import pytest

from model import geometry as g
from model import review, skeleton, stages

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


INSPECT = """
import json, bpy
def walk(lc):
    yield lc
    for c in lc.children:
        yield from walk(c)
a = bpy.data.scenes["Assembled"]
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
for f in range(a.frame_start, a.frame_end + 2):
    a.frame_set(f)
    for o in horns:
        deg[o.name[5:]].append(o["deg"])
out["horns"] = {h: [min(v), max(v), v[0], v[-1]] for h, v in deg.items()}
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
"""


@pytest.fixture(scope="module")
def blend():
    path = os.environ.get("NOGGIN_REVIEW")
    if not path or not os.path.isfile(path):
        pytest.skip("no review file to read (NOGGIN_REVIEW: just review sets it)")
    r = subprocess.run(
        [skeleton.BLENDER, "-b", "--factory-startup", path, "--python-expr", INSPECT], capture_output=True, text=True
    )
    line = next(x for x in r.stdout.splitlines() if x.startswith("INSPECT "))
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
    assert (blend["morty"] == 3) == os.path.isfile(review.MORTY)
    assert blend["helpers"]


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


def test_mortys_bust_stops_at_the_models_flat_floor(blend):
    if not blend["morty"]:
        pytest.skip("no local Morty reference")
    low, caps = blend["bust"]
    assert low == pytest.approx(blend["floor"], abs=0.01)
    assert caps > 0


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
