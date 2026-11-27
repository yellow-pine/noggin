"""Seam: the review file as model/review writes it (#915): light checks of its plan (the loop, the plates, the lock),
and the written .blend itself read by headless Blender, locally once `just review` wrote it (NOGGIN_REVIEW names it:
the recipe runs this file after each build)."""

import inspect
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pytest
import trimesh

from model import geometry as g
from model import review, skeleton, skin, stages
from scripts import heavy

STAGE = stages.STAGES[review.DOC]


def test_the_loop_takes_every_horn_to_each_end_of_its_range_and_back_to_rest():
    """Each horn's keys reach its limits, its servo's range (ADR 0011), and are 0 on the loop's first and last frame."""
    for horn, pts in review.keys(STAGE).items():
        degs = [d for _, d in pts]
        assert (min(degs), max(degs)) == pytest.approx(STAGE.horns[horn].limits), horn
        assert pts[0] == (1, 0.0) and pts[-1] == (review.FRAMES, 0.0)


def test_the_loop_moves_the_lower_lids_with_the_blink_and_the_eyes_with_the_pitch():
    """#967: the review's motion is stages.pose at each key, which left a horn's Rods at rest: no lower lid ever moved
    in the file, nor an eye up or down. By the blink's shut each lower lid has risen on its link and by the pitch's
    ends each eye has pitched on its push-rod."""
    rest = {n: p.matrix for n, p in STAGE.parts.items()}
    at = dict(review.motion(STAGE, review.keys(STAGE)))

    def turned(frame, name):
        m = at[frame][name] @ np.linalg.inv(rest[name])
        return np.degrees(np.arccos(np.clip((np.trace(m[:3, :3]) - 1) / 2, -1, 1)))

    for s in "LR":  # the loop poses the odd frames: one before the blink's shut, one off each of the pitch's ends
        assert turned(219, f"{s} lower lid:1") > 40 and turned(219, f"{s} lid link:1") > 1
        for frame in (189, 199):
            assert turned(frame, f"{s} eyeball cap:1") > 10 and turned(frame, f"{s} push-rod:1") > 1


def test_the_bones_ride_their_regions():
    """The skull and mandible in Skull, the atlas and axis in Mechanism, the Torso in Pedestal."""
    region = review.regions()
    assert region["worn skull:1"] == region["worn mandible:1"] == "Skull"
    assert region["atlas:1"] == region["axis:1"] == "Mechanism"
    assert region["torso:1"] == "Pedestal"


SHELLS = [f"{k} {n}:1" for k, names in g.SHELLS.items() for n in names]  # every Shell cut from a Sculpt
CAPS = ["L eyeball cap:1", "R eyeball cap:1"]  # the eye whites, the mechanism's own


def test_the_review_wears_mortys_skin_whatever_the_documents_wear():
    """#850, #998: the review shows the newest Skin, failing its wearing gates or not. Its own copy of the Stage 3
    document has every Shell cut from the Sculpt beside what the document has, and its Skin layer is those Shells and
    the eyeball caps, the eye whites."""
    worn = review.worn()
    assert len(SHELLS) == 4 and set(worn.parts) == set(STAGE.parts) | set(SHELLS)
    assert {n for n, p in worn.parts.items() if review.layer(p.file) == "Skin"} == {*SHELLS, *CAPS}
    region = review.regions()
    assert region["morty hair:1"] == region["morty face:1"] == region["morty chin:1"] == "Skull"
    assert region["morty shirt:1"] == "Pedestal"


def test_each_shell_moves_with_what_carries_its_motion_region_and_the_shirt_with_nothing():
    """#969: the hair and the face turn with the head, the chin with the jaw, the shirt stays fixed through every
    horn's range."""
    worn = review.worn()
    rest = {n: p.matrix for n, p in worn.parts.items()}

    def moved(mats, part):
        return mats[part] @ np.linalg.inv(rest[part])

    for horn, h in worn.horns.items():
        for deg in h.limits:
            mats = stages.pose(worn, horn, deg).parts
            np.testing.assert_allclose(mats["morty shirt:1"], rest["morty shirt:1"])
            for shell, carrier in (("hair", "gimbal frame"), ("face", "gimbal frame"), ("chin", "jaw")):
                np.testing.assert_allclose(
                    moved(mats, f"morty {shell}:1"), moved(mats, f"{carrier}:1"), atol=1e-9, err_msg=f"{shell} {horn}"
                )
    pan = stages.pose(worn, "pan horn", worn.horns["pan horn"].limits[1]).parts
    jaw = stages.pose(worn, "jaw horn", worn.horns["jaw horn"].limits[0]).parts
    assert not np.allclose(pan["morty hair:1"], rest["morty hair:1"])
    assert not np.allclose(jaw["morty chin:1"], rest["morty chin:1"])
    np.testing.assert_allclose(jaw["morty face:1"], rest["morty face:1"])


def test_pack_keeps_every_piece_on_a_plate_clear_of_its_edge():
    """Each footprint inside its plate, GAP from the edge; a new plate once one is full; too big a piece refused."""
    sizes = [(120, 100), (200, 60), (90, 90), (240, 30), (100, 120), (50, 50)] * 3
    for (w, d), (_, x, y) in zip(sizes, review.pack(sizes), strict=True):
        assert review.GAP <= x and x + w <= review.BED - review.GAP
        assert review.GAP <= y and y + d <= review.BED - review.GAP
    assert len({p for p, _, _ in review.pack(sizes)}) > 1
    with pytest.raises(ValueError):
        review.pack([(review.BED, 10)])


def test_the_review_finishes_at_the_print_files_pitch_unless_coarse_is_asked_for():
    """#993: `just review` alone finishes the bones at skeleton.PITCH, the print files' voxel; coarse stays an option."""
    assert review.QUALITY["production"] == skeleton.PITCH < review.QUALITY["coarse"]
    for f in (review.job, review.build):
        assert inspect.signature(f).parameters["quality"].default == "production"
    just = open(os.path.join(stages.REPO, "justfile")).read()
    assert 'review quality="production"' in just and '_review-build quality="production"' in just


def test_a_piece_lies_on_its_largest_face_that_fits_a_plate():
    """#992: a piece whose largest face lies past a plate lies on the next largest that fits, here its 200 x 30 end."""
    box = trimesh.creation.box((250.0, 30.0, 200.0))
    laid = trimesh.transform_points(box.vertices, review.flat(box)).max(axis=0)
    assert laid == pytest.approx((200.0, 30.0, 250.0))


def test_a_second_writer_is_refused_while_the_lock_is_held(tmp_path):
    path = str(tmp_path / "review.blend.lock")
    held = review.lock(path)
    with pytest.raises(SystemExit, match="another writer"):
        review.lock(path)
    held.close()
    review.lock(path).close()


def test_the_blender_slot_is_taken_again_at_once_under_the_command_that_holds_it(tmp_path):
    """#1026: `just test` runs these tests under scripts/heavy.py, whose lock the slot is, and each waited on it forever."""
    env = {**os.environ, "NOGGIN_HEAVY_LOCK": str(tmp_path / "heavy.lock")}
    code = "from model import review; review.lock(review.SLOT, wait=True).close(); print('ran')"
    under = [sys.executable, heavy.__file__, sys.executable, "-c", code]
    done = subprocess.run(under, env=env, cwd=stages.REPO, capture_output=True, text=True, timeout=30)
    assert (done.returncode, done.stdout) == (0, "ran\n")


REFERENCE_CARRIERS = {r: c for r, c in review.CARRIERS.items() if c}  # the moving Motion regions'
# {a Shell cut from the Sculpt: the live part its Motion region rides, None for the fixed body's}
SKIN_CARRIERS = {s: review.CARRIERS[skin.region(s.removesuffix(":1"))] for s in SHELLS}


def test_the_reference_rides_the_same_live_parts_as_the_shells_of_its_regions():
    """#969: a reference surface's carrier is its Motion region's (skin.MOTION), the part a Shell of that region rides,
    and it is in the review's document; the body's regions have none, and the neck's is the head's (docs/adr/0030)."""
    assert set(review.CARRIERS) == set(skin.MOTION)
    assert review.CARRIERS["shoulders"] is review.CARRIERS["torso"] is None
    assert review.CARRIERS["neck"] == review.CARRIERS["head"] == "gimbal frame:1"
    assert set(REFERENCE_CARRIERS.values()) <= set(STAGE.parts)


def test_the_reference_is_cut_along_mortys_cuts_on_his_sculpt():
    """#992, #893's directive: the review cuts Morty's reference along skin.cuts(), the one source the printed Shells
    are split along too (ADR 0011), each cut in its view and where it sits on the sculpt."""
    cuts = skin.cuts()
    assert review.contours().keys() == cuts.keys()
    for name, (view, region) in review.contours().items():
        assert view == cuts[name][0]
        np.testing.assert_allclose(region, cuts[name][1])


HEAD = np.linalg.inv(stages.align(*stages.DOCS[review.DOC]["eyes"])).tolist()  # world to the head's frame
INSPECT = (
    "import json, bmesh, bpy, numpy as np\n"
    f"EXPECTED_REFERENCE = {REFERENCE_CARRIERS!r}\nCONTOURS = {review.contours()!r}\nHEAD = np.array({HEAD!r})\n"
    f"LAYERS = {tuple(review.ALPHA)!r}\nSKIN_CARRIERS = {SKIN_CARRIERS!r}\n"
    + """
def off(points, poly):
    # each (n, 2) point's distance to the closed polygon's sides
    a = np.asarray(poly)
    d = np.roll(a, -1, axis=0) - a
    t = np.clip(((points[:, None] - a) * d).sum(-1) / np.maximum((d * d).sum(-1), 1e-12), 0, 1)
    return np.linalg.norm(points[:, None] - (a + t[..., None] * d), axis=-1).min(axis=1)
def seams(objects):
    # {region: {Colour group: faces}}, {region seam: the most mm a seam's vertex lies off the cut it was made along}:
    # a Colour group's seam on its cut, an eye's open edge on its eye white's
    sections, out = {}, {}
    for o in objects:
        region = o["reference_region"]
        names = [m.name for m in o.data.materials]
        bm = bmesh.new()
        bm.from_mesh(o.data)
        group = {f: names[f.material_index] for f in bm.faces}
        sections[region] = {g: sum(1 for x in group.values() if x == g) for g in set(group.values())}
        m = HEAD @ np.array(o.matrix_world)
        for e in bm.edges:
            pair = sorted({group[f] for f in e.link_faces})
            if len(e.link_faces) == 1 and region[2:] == "eye":
                key = f"{region[0]} eye white"
            elif len(pair) == 2:
                # the shirt's edge is the collar's, against the hair too (the fixed body's shirt takes the hair's)
                key = "collar" if "clothes" in pair else "hairline" if "hair" in pair else f"{region[0]} pupil"
            else:
                continue
            view, poly = CONTOURS[key]
            p = np.array([(m @ [*v.co, 1])[:3] for v in e.verts])
            p = p[:, [1, 2]] if view == "side" else p[:, [0, 2]]
            out[f"{region} {key}"] = max(out.get(f"{region} {key}", 0.0), float(off(p, poly).max()))
        bm.free()
    return sections, out
def walk(lc):
    yield lc
    for c in lc.children:
        yield from walk(c)
a = bpy.data.scenes["Assembled"]
tops = a.view_layers[0].layer_collection.children
out = {"scenes": [s.name for s in bpy.data.scenes], "first": bpy.context.window_manager.windows[0].scene.name}
out["hidden"] = sorted(l.name for l in tops if l.hide_viewport)
tops["Morty"].hide_viewport = False  # switched on, for what follows reads it moving
a.frame_set(a.frame_start)
out["layers"] = {c.name: {k.name: sorted({round(o.color[3], 2) for o in k.objects}) for k in c.children}
                 for c in bpy.data.collections if c.name in LAYERS}
out["layer_material_alpha"] = {c.name: sorted({round(slot.material.diffuse_color[3], 2)
    for o in c.all_objects for slot in o.material_slots if slot.material})
    for c in bpy.data.collections if c.name in LAYERS}
out["skin_layer"] = {o["part"]: {"region": next(k.name for k in o.users_collection), "colour": list(o.color),
    "material": [list(s.material.diffuse_color) for s in o.material_slots], "travel": 0.0, "carrier_error": 0.0,
    "visible": o.visible_get(view_layer=a.view_layers[0])} for o in bpy.data.collections["Skin"].all_objects}
out["morty"] = len(bpy.data.collections["Morty"].all_objects)
out["shading"] = a.display.shading.color_type
out["sections"], out["seams"] = seams([o for o in bpy.data.collections["Morty"].all_objects if o.get("reference_region")])
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
shells = {n: (actors[n], np.array(actors[n].matrix_world), c and (actors[c], np.linalg.inv(actors[c].matrix_world)))
          for n, c in SKIN_CARRIERS.items() if n in actors}
actor_rest = {role: np.array(actors[part].matrix_world) for role, part in EXPECTED_REFERENCE.items() if part in actors}
actor_back = {role: np.linalg.inv(m) for role, m in actor_rest.items()}
out["carriers"] = {part: [] for part in EXPECTED_REFERENCE.values() if part in actors}
out["reference_motion"] = {o["reference_region"]: {"vertices": len(v), "travel": 0.0,
    "carrier_error": None, "own_travel": 0.0}
    for o, v, rest in reference.values()}
for f in range(a.frame_start, a.frame_end + 2):
    a.frame_set(f)
    for o in horns:
        deg[o.name[5:]].append(o["deg"])
    for part, mats in out["carriers"].items():
        mats.append([f, [list(r) for r in actors[part].matrix_world]])
    for n, (o, rest, carrier) in shells.items():  # a Shell's travel, and how far it strays from what carries it
        now, s = np.array(o.matrix_world), out["skin_layer"][n]
        s["travel"] = max(s["travel"], float(abs(now - rest).max()))
        if carrier:
            expected = np.array(carrier[0].matrix_world) @ carrier[1] @ rest
            s["carrier_error"] = max(s["carrier_error"], float(abs(now - expected).max()))
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
    """Mech, Skeleton, Skin and Morty, each in Skull, Mechanism and Pedestal, every object at the layer's alpha;
    Morty's objects only with the local reference (a fresh clone builds without them), and his layer a toggle, off
    when the file opens: the Skin's Shells show his surface (#850)."""
    for layer, alpha in review.ALPHA.items():
        regions = blend["layers"][layer]
        assert sorted(regions) == sorted(f"{layer} {r}" for r in ("Skull", "Mechanism", "Pedestal"))
        assert all(a in ([], [alpha]) for a in regions.values()), (layer, regions)
        assert blend["layer_material_alpha"][layer] in ([], [alpha])
    assert bool(blend["morty"]) == os.path.isfile(review.MORTY)
    assert blend["helpers"] and blend["hidden"] == ["Morty", "helpers"]
    assert blend["reference_visible_without_mech"]


def test_the_skin_layer_is_mortys_shells_and_the_caps_in_the_skins_colours_each_with_what_carries_it(blend):
    """#850: the four Shells cut from the Sculpt and the eyeball caps, seen when the file opens, each in its Colour
    group's filament (the Default Skin palette) at the Skin's alpha; through the loop the hair, the face and the chin
    stay on what carries them and the shirt never moves."""
    layer = blend["skin_layer"]
    assert set(layer) == {*SHELLS, *CAPS}
    for part, shell in layer.items():
        hex_ = g.filament(g.PRINTED[part.removesuffix(":1")][0], review.PRESET)[3]
        srgb = [int(hex_[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
        assert shell["colour"] == pytest.approx([*linear, review.ALPHA["Skin"]], abs=1e-4), part
        assert shell["material"] == [pytest.approx(shell["colour"])] and shell["visible"], part
    assert {s["region"] for n, s in layer.items() if n != "morty shirt:1"} == {"Skin Skull"}
    assert layer["morty shirt:1"]["region"] == "Skin Pedestal" and layer["morty shirt:1"]["travel"] < 1e-6
    for part in ("morty hair:1", "morty face:1", "morty chin:1"):
        assert layer[part]["travel"] > 1.0 and layer[part]["carrier_error"] < 1e-3, part


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


def test_the_reference_shoulders_and_torso_stay_fixed_while_the_head_moves_and_the_necks_skin_rides_it(blend):
    """#969, as Cansin changed it on 2026-11-27 (docs/adr/0030): the neck's skin turns and nods with the head, as one
    with it; the shoulders and the torso never move. Read at each region's vertices and at its witnesses."""
    if not blend["morty"]:
        pytest.skip("no local Morty reference")
    motion = blend["reference_motion"]
    assert {"neck", "shoulders", "torso", "head"} <= motion.keys()
    for name in ("shoulders", "torso"):
        assert motion[name]["vertices"] >= 3
        assert motion[name]["travel"] == pytest.approx(0.0, abs=1e-3), name
    assert motion["head"]["travel"] > 1.0 and motion["neck"]["travel"] > 1.0
    assert motion["neck"]["vertices"] >= 3 and motion["neck"]["own_travel"] < 1e-3  # none of its own against the head
    for name, role in {"neck": "neck", "L shoulder": "shoulders", "R shoulder": "shoulders"}.items():
        witnesses = blend["reference_witnesses"]["witness " + name]
        assert all(w["region"] == role and w["vertices"] > 0 for w in witnesses), name
        assert all((w["travel"] > 1.0) if role == "neck" else (w["travel"] < 1e-3) for w in witnesses), name


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
    assert {"head", "jaw", "L eye", "R eye"} <= motion.keys()
    for role in REFERENCE_CARRIERS.keys() & motion.keys():
        assert motion[role]["vertices"] > 0
        assert motion[role]["carrier_error"] is not None, role
        assert motion[role]["carrier_error"] < 1e-3, role
    assert motion["head"]["own_travel"] < 1e-3
    assert all(motion[role]["own_travel"] > 1.0 for role in ("jaw", "L eye", "R eye"))
    assert motion["neck"]["carrier_error"] < 1e-3  # on the head's carrier


LIDS = {f"{s} {lid} lid" for s in "LR" for lid in ("upper", "lower")}


def test_mortys_reference_is_cut_along_his_cuts(blend):
    """#992: every Colour group's seam and each eye white's edge lies on the cut it was made along (skin.cuts), so no
    boundary steps along the sculpt's triangles."""
    if not blend["morty"]:
        pytest.skip("no local Morty reference")
    seams = blend["seams"]
    assert {"head hairline", "L eye L eye white", "R eye R eye white", "L eye L pupil", "R eye R pupil"} <= seams.keys()
    assert any(k.endswith(" collar") for k in seams)
    assert max(seams.values()) < 0.01, seams


def test_each_cut_sits_on_its_own_motion_region(blend):
    """#992, #969: each eye is its dome alone, all eye white but its pupil; the shirt is on the fixed body alone and the
    jaw under the mouth line in the face's colour; no surface is a lid's (Cansin, 2026-11-27: the lids are the
    mechanism's covers, the reference has no lid ring)."""
    if not blend["morty"]:
        pytest.skip("no local Morty reference")
    sections = blend["sections"]
    assert not LIDS & sections.keys()

    def where(group):
        return {r for r, counts in sections.items() if counts.get(group)}

    assert where("pupils") == where("eye whites") == {"L eye", "R eye"}
    assert all(set(sections[f"{s} eye"]) == {"pupils", "eye whites"} for s in "LR")
    assert where("clothes") <= {"neck", "shoulders", "torso"}
    assert set(sections["torso"]) == {"clothes"}  # under the collar the shirt, behind the hairline's end too
    assert set(sections["jaw"]) == {"face"}


def test_each_reference_carrier_moves_where_the_document_poses_it(blend):
    """#969: a carrier hidden in helpers (an eyeball cap, a Shell) is keyed too, so what it carries moves: each one's
    world matrix on every keyed frame is the document's pose there."""
    poses = dict(review.motion(STAGE, review.keys(STAGE)))
    assert blend["carriers"].keys() == set(REFERENCE_CARRIERS.values())
    for part, frames in blend["carriers"].items():
        checked = [(f, m) for f, m in frames if f in poses]
        assert len(checked) > 10, part
        for f, m in checked:
            np.testing.assert_allclose(m, poses[f][part], atol=1e-3, err_msg=f"{part} at frame {f}")


def test_exploded_and_print_bed_materials_are_opaque(blend):
    assert blend["material_alpha"] == {"Exploded": [1.0], "Print bed": [1.0]}


def test_every_printed_piece_lies_on_a_plate(blend):
    """Each plate's pieces inside its BED square, on it (z 0 and up); every printed part placed once, the Shells the
    review wears too."""
    n = 0
    for plate, (x0, y0, z0, x1, y1, count) in blend["plates"].items():
        assert -0.5 <= x0 and x1 <= review.BED + 0.5 and -0.5 <= y0 and y1 <= review.BED + 0.5, plate
        assert z0 >= -0.5, plate
        n += count
    assert n == len(review.plates(review.worn())) == len(review.plates(STAGE)) + len(SHELLS)


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
    for group in (('clothes','face') if role=='torso' else ('face','clothes')):  # every slot the contours paint it
        mesh.materials.append(bpy.data.materials.get(group) or bpy.data.materials.new(group))
    obj=bpy.data.objects.new(role,mesh)
    obj['reference_region']=role
    obj['display_region']='Pedestal' if role=='torso' else 'Mechanism' if role=='neck' else 'Skull'
    if role=='head': obj['carrier']='carrier:1'  # the one CARRIERS names, which it must agree with
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
     'rest':{'carrier:1':list(identity)},'orbits':[],'belts':[],'vault':{'bones':[],'middle':[0,0,0]},'numbers':{},
     'parts':{'carrier:1':{'region':'Skull','layer':'Mech','colour':'#FFFFFF'},
              'worn skull:1':{'region':'Skull','layer':'Skeleton','colour':'#FFFFFF'}},
     'alpha':{'Mech':1,'Skeleton':.69,'Morty':.33},
     'motion':[[1,{'carrier:1':list(identity)}]],
     'morty':{'blend':str(source),'at':list(at),'floor':1538,
              'colours':{'face':'#F7CED7','clothes':'#FFFFFF'},
              'carriers':{'head':'carrier:1','neck':None,'shoulders':None,'torso':None},
              'head':list(identity),'contours':CONTOURS}}
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
    prefix += f"CONTOURS={review.contours()!r}\n"
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
