"""Seam: the realistic Skeleton's bones as the Skeleton scene exports them (model/skeleton finish(), just ours; docs/adr/
0025): on the Mech's eyes and neck, under Morty's skin (envelope.py), one piece each; the scene itself committed
light, its one source under its own licence."""

import functools
import itertools
import os
import subprocess

import manifold3d as m3
import numpy as np
import pytest
import trimesh
from scipy.spatial import cKDTree

from model import geometry as g
from model import gimbal as gm
from model import mjcf, skeleton, stages
from model import neck as nk
from model import skin as sk
from model.morty import shells
from model.skeleton import envelope, fit

SCENE = os.path.join(stages.REPO, skeleton.SCENE)
CAP_MB = 12.0  # the scene's size cap: #872's warped scene saved 11 MB without Morty (no LFS: docs/adr/0025)
SKIN_TOL = 0.2  # a depth under Morty's skin is good to this (envelope.DENSITY), mm
# strict, so #968's follow-up, which re-measures nk.MANDIBLE_CHAIN on the refitted mandible, drops the mark
CHAIN = "#968: the jaw carrier's chain still follows the box-fitted mandible, not #874's refit inside Morty's skin"


def test_the_scene_is_committed_compressed_under_its_cap_without_lfs():
    """Blender's compressed .blend (zstd's magic first), at most CAP_MB, and no LFS filter on it."""
    with open(SCENE, "rb") as f:
        assert f.read(4) == b"\x28\xb5\x2f\xfd"
    assert os.path.getsize(SCENE) <= CAP_MB * 1e6
    attr = subprocess.run(["git", "check-attr", "filter", "--", skeleton.SCENE], cwd=stages.REPO, capture_output=True)
    assert b"lfs" not in attr.stdout


def test_the_bones_sit_under_their_sources_licence():
    """docs/adr/0023, 0025: BodyParts3D's licence (treated as CC BY-SA 2.1 JP) beside the scene that holds its bones, and
    the old sources gone."""
    notice = open(os.path.join(stages.REPO, "model/skeleton/LICENSE.md")).read()
    assert "dbarchive.biosciencedbc.jp" in notice and "creativecommons.org/licenses/by-sa/2.1/jp/" in notice
    assert "not under the repo's PolyForm Noncommercial licence" in notice and skeleton.SCENE in notice
    assert not os.path.exists(os.path.join(stages.REPO, "model/skull"))


def test_the_exporter_cuts_the_calvaria_off_each_skulls_own_finish():
    """#874: the calvaria has no bones of its own in the scene and no carving of its own. The exporter gets it as the
    skull's cap (job()["cap"]): the bare and the worn skull each with its calvaria, the seam level in the head's
    frame over the lids' shell (the eyes at z 0), the two faces a Seat's gap apart, and three Seats on it, well
    apart, in the Skin's own sizes (model/skin.py)."""
    job = skeleton.job()
    assert set(job["bones"]) == set(g.SKULL) - {skeleton.CAP}
    cap = job["cap"]
    assert cap["of"] == {"skull": "calvaria", "worn skull": "worn calvaria"}
    assert cap["seam"] - cap["gap"] / 2 > skeleton.LID_SHELL + skeleton.CLEAR_MM + skeleton.FLOOR
    spots = np.array(cap["seats"])
    assert spots.shape == (3, 2)
    assert min(np.linalg.norm(a - b) for a, b in itertools.combinations(spots, 2)) > 100.0
    assert (cap["gap"], cap["boss"], cap["bore"]) == (sk.GAP, sk.PAD_R, [sk.MAGNET[0] / 2 + sk.FIT, sk.MAGNET[1]])
    assert (cap["ball"], cap["groove"]) == ([sk.RING, sk.BALL_R], [sk.GROOVE, sk.GROOVE_D])


@functools.cache
def _bones():
    return {stem: trimesh.load(stages.stl(stem), force="mesh") for stem in g.BONES}


@pytest.mark.model
@pytest.mark.bones
def test_the_skulls_eyes_sit_in_its_orbits():
    """Each eye's centre, on the Sculpt's own, inside the cranium's box, and the forehead over the lids' shell
    ahead of them. No brow stands in front of the eyes any more (ADR 0025's amendment of 2026-11-26): the lids stow in
    a shell 38 mm round each eye centre (#967), which takes the orbits' rims, and Morty's own forehead lies behind
    where an anatomical brow would. The skull's height is Morty's to give
    (test_each_bone_lies_under_mortys_skin), no box's."""
    lo, hi = _bones()["skull"].bounds
    for e in map(np.array, gm.EYE.values()):
        assert (lo <= e).all() and (e <= hi).all() and lo[1] < e[1]


@pytest.mark.model
@pytest.mark.bones
def test_the_skull_keeps_out_of_the_lids_shell_and_the_belt_behind_each_eye():
    """#967's re-laid lids stow in a shell of radius skeleton.LID_SHELL all round each of Morty's eye centres
    (gimbal.EYE) and their drives leave it through the belt behind the eye (skeleton.BELT): no bone of the finished
    skull within the shell or in the belt, to the Finish's voxel."""
    v = _bones()["skull"].vertices
    for x, y, z in gm.EYE.values():
        assert np.linalg.norm(v - (x, y, z), axis=1).min() >= skeleton.LID_SHELL + skeleton.CLEAR_MM - skeleton.PITCH
        lo = np.array((x - skeleton.BELT[0], y, z + skeleton.BELT_Z[0])) + skeleton.PITCH
        hi = np.array((x + skeleton.BELT[0], y + skeleton.BELT[1], z + skeleton.BELT_Z[1])) - skeleton.PITCH
        assert not ((v > lo) & (v < hi)).all(axis=1).any()


@pytest.fixture(scope="module")
def skin():
    """Morty's skin as a depth, taken in a fixture: its build is 144 s of CPU, over the 60 s a test gets on CI's
    four shared cores, where the timeout cut it off mid-query and the worker crashed (#874's first full Checks
    runs). One worker builds it and the others wait for its file (envelope.morty())."""
    return envelope.morty()


@pytest.mark.model
@pytest.mark.bones
@pytest.mark.parametrize("stem", g.BONES)
def test_each_bone_lies_under_mortys_skin(stem, skin):
    """Every finished bone at least envelope.ROOM (the Skin's wall and its clearance) under Morty's skin, the sculpt's
    surface, to SKIN_TOL: the skull's limit since 2026-11-27, where the compact head's box was (#893, #874). On main
    before the refit the forehead stood 10.9 mm out of him, the chin 4.6 and C7's spine 8.6."""
    depth = skin.depth(trimesh.load(stages.stl(stem), force="mesh").vertices)
    assert depth.min() >= envelope.ROOM - SKIN_TOL


@pytest.mark.model
@pytest.mark.bones
def test_the_vertebrae_ring_the_pan_axis_under_the_tilt_axis():
    """The atlas's canal round the pan axis, its top under the tilt axis (C0, the occipital condyles on it), the axis
    under it and each vertebra under the one above."""
    bones = _bones()
    pan, tilt = nk.HEAD_AXES["pan"][0], nk.HEAD_AXES["tilt"][0]
    assert fit.canal(bones["atlas"]) == pytest.approx(pan[:2], abs=1.0)
    assert bones["atlas"].bounds[1][2] < tilt[2]
    assert all(bones[a].bounds[0][2] < bones[b].bounds[0][2] for b, a in zip(g.NECK, g.NECK[1:]))


@pytest.mark.model
@pytest.mark.bones
def test_the_vault_is_closed_from_the_sides_the_back_and_above():
    """Seen from the head's middle at the eyes' height, the finished skull shows bone in every direction (2 deg a
    bin) level with the eyes and above, but in front, where the face opens round the lids. Two holes stood open at
    the temples (the R about 19 x 10 mm) where the parietal bones are 0.8 to 2.2 mm thick, under the print floor,
    and the Finish rounded them away: it now thickens the vault's bones inward first (skeleton.THICK; Cansin,
    2026-11-27, #893)."""
    rng = np.random.default_rng(0)
    whole = trimesh.util.concatenate([_bones()[stem] for stem in (skeleton.CAPPED, skeleton.CAP)])  # its cap on
    p = np.asarray(trimesh.sample.sample_surface(whole, 2_000_000, seed=rng)[0]) - (0.0, 70.0, 0.0)
    az = np.degrees(np.arctan2(p[:, 0], p[:, 1]))  # 0 behind, 90 at his left
    el = np.degrees(np.arcsin(p[:, 2] / np.linalg.norm(p, axis=1)))
    seen = np.zeros((120, 45), bool)  # az -120 to 120, el 0 to 90
    at = (np.abs(az) < 120) & (el >= 0)
    seen[((az[at] + 120) // 2).astype(int), (el[at] // 2).astype(int)] = True
    # straight up, the last 2 deg are one cap: a bin there is 0.26 mm2 of skull and gets 5 samples, so one in two
    # skulls left a bin of it empty by chance (#1075: 3 of 120 on a whole crown, none at 12 million samples)
    seen[:, -1] = seen[:, -1].any()
    assert [(int(a) * 2 - 119, int(e) * 2 + 1) for a, e in np.argwhere(~seen)] == []


CAPS = [(skeleton.CAPPED, skeleton.CAP), (g.WORN[skeleton.CAPPED], g.WORN[skeleton.CAP])]  # bare, and worn


@pytest.mark.model
@pytest.mark.bones
@pytest.mark.parametrize("skull,cap", CAPS)
def test_the_calvaria_comes_off_the_skull_along_a_level_seam(skull, cap):
    """#874: the skull ends flat at the seam (skeleton.SEAM_Z, in the head's frame), but for its Seats' balls, and its
    calvaria starts flat a Seat's gap above (skin.GAP, half from each), so the cap lifts off and prints lying on its
    rim. The two flat faces are one ring's two sides: as large as each other, and over 2000 mm2 (a ring about 515 mm
    round and 5 mm wide, measured, with its three bosses). Each piece is closed: every edge between two faces."""
    bones = _bones()
    below, above = skeleton.SEAM_Z - sk.GAP / 2, skeleton.SEAM_Z + sk.GAP / 2
    assert bones[skull].bounds[1][2] == pytest.approx(below + sk.BALL_R, abs=0.02)  # a ball's top
    assert bones[cap].bounds[0][2] == pytest.approx(above, abs=0.02)
    assert bones[skull].is_watertight and bones[cap].is_watertight

    def face(mesh, z, up):
        on = (np.abs(mesh.triangles_center[:, 2] - z) < 0.02) & (mesh.face_normals[:, 2] * up > 0.99)
        return mesh.area_faces[on].sum()

    rim, seat = face(bones[cap], above, -1.0), face(bones[skull], below, 1.0)
    assert rim > 2000.0 and rim == pytest.approx(seat, rel=0.02)


def _share(bone, solid):
    """How much of `solid` (manifold3d) is the bone's."""
    return (bone ^ solid).volume() / solid.volume()


@pytest.fixture(scope="module")
def solids():
    """{piece: its solid (manifold3d)}, each skull and its calvaria: built once, 5 s of the four."""
    return {stem: shells._solid(_bones()[stem].vertices, _bones()[stem].faces) for pair in CAPS for stem in pair}


@pytest.mark.model
@pytest.mark.bones
@pytest.mark.parametrize("skull,cap", CAPS)
@pytest.mark.parametrize("spot", range(len(skeleton.SEATS)))
def test_the_calvaria_sits_on_a_seat_at_each_boss(skull, cap, spot, solids):
    """#874: at each of skeleton.SEATS the skull and its calvaria have a Seat's two halves (model/skin.py, the Skin's
    own). Each has a pocket open from its face of the seam, a magnet deep (skin.MAGNET, its fit round), so the pair
    stands face to face skin.GAP apart, with the print floor of bone (skeleton.FLOOR) round it and behind it, in the
    wall or the boss on its inner side (round it in the calvaria from its grooves' depth on). Three balls stand on the skull's face round its pocket and rest in three
    V-grooves in the calvaria's: each ball whole, the two pieces sharing nothing, and a ball 0.05 mm larger already
    in the groove's sides. And the boss stays inside the wall: straight out from the Seat the skull's outer face is
    nowhere nearer its middle than the boss's radius and half a mm."""
    x, y = skeleton.SEATS[spot]
    bore, depth = sk.MAGNET[0] / 2 + sk.FIT, sk.MAGNET[1]
    out = np.array([x, y]) - fit.MIDDLE[:2]
    out /= np.linalg.norm(out)
    solid = solids
    for stem, up in ((skull, -1.0), (cap, 1.0)):  # the pocket runs down into the skull, up into its calvaria

        def disc(r, z0, z1, up=up):
            """A disc of radius r on the Seat's axis, from z0 to z1 into the piece from its face of the seam."""
            lo, hi = sorted(skeleton.SEAM_Z + up * (sk.GAP / 2 + z) for z in (z0, z1))
            return m3.Manifold.cylinder(hi - lo, r, circular_segments=96).translate((x, y, lo))

        assert _share(solid[stem], disc(sk.MAGNET[0] / 2, -0.05, depth)) < 1e-3  # the magnet's room, flush
        top = sk.GROOVE_D + 0.01 if stem == cap else 0.0  # a Seat's grooves start 0.9 mm from its pocket
        assert _share(solid[stem], disc(bore + skeleton.FLOOR, top, depth) - disc(bore, -1.0, depth + 1.0)) > 0.99
        assert _share(solid[stem], disc(bore, depth + 0.01, depth + skeleton.FLOOR)) > 0.99
        v = _bones()[stem].vertices
        outer = v[(v[:, :2] - (x, y)) @ out > sk.RING + sk.GROOVE + 0.2]  # past the Seat's own grooves
        assert np.linalg.norm(outer - (x, y, skeleton.SEAM_Z), axis=1).min() >= sk.PAD_R + 0.5
    assert (solid[skull] ^ solid[cap]).volume() < 0.1
    for deg in (0, 120, 240):
        at = (
            x + sk.RING * np.cos(np.radians(deg)),
            y + sk.RING * np.sin(np.radians(deg)),
            skeleton.SEAM_Z - sk.GAP / 2,
        )
        above = m3.Manifold.sphere(sk.BALL_R, 48).translate(at).trim_by_plane((0, 0, 1), at[2] + 0.01)
        assert _share(solid[skull], above) > 0.99
        assert (solid[cap] ^ m3.Manifold.sphere(sk.BALL_R + 0.05, 48).translate(at)).volume() > 0


def test_the_seats_magnets_hold_the_calvaria_on_whichever_way_up_the_head_is():
    """#874: the three pairs, skin.GAP apart, pull the calvaria on with at least skin.SF times its printed weight
    (inferred, like every Seat's hold: no build settles one yet)."""
    pytest.importorskip("magpylib")
    if not os.path.exists(stages.stl(skeleton.CAP)):
        pytest.skip("no finished calvaria here (just ours, with Blender)")
    mesh = trimesh.load(stages.stl(skeleton.CAP), force="mesh")
    newtons = mjcf.mass(mesh, stages.printed(skeleton.CAP)) / 1000 * 9.81
    assert len(skeleton.SEATS) * sk.hold_n() >= sk.SF * newtons


@pytest.mark.model
@pytest.mark.bones
@pytest.mark.parametrize("stem", g.BONES)
def test_each_bone_fits_the_printers_bed(stem):
    """#874's acceptance: every piece whole on the bed (g.BED each way), the calvaria split off its skull."""
    lo, hi = trimesh.load(stages.stl(stem), force="mesh").bounds
    assert (hi - lo).max() <= g.BED


@pytest.mark.model
@pytest.mark.bones
def test_the_calvaria_lifts_straight_off_the_mechanism():
    """#874: the cap is there so the head's mechanism can be reached. At rest nothing of the document but the
    skull's own bones stands over any of the calvaria, bosses and all: it lifts straight up, and comes down the same
    way. Read in plan on a 1 mm grid: the lowest of the calvaria in each square against the highest of each part."""
    stage = stages.STAGES[skeleton.DOC]
    worn = g.WORN[skeleton.CAP]
    head = np.linalg.inv(stage.parts[f"{worn}:1"].matrix)  # the document's frame into the calvaria's own
    cap = trimesh.load(stages.stl(worn), force="mesh")
    lowest = {}
    for (i, j), z in zip(map(tuple, np.floor(cap.vertices[:, :2]).astype(int)), cap.vertices[:, 2], strict=True):
        lowest[i, j] = min(z, lowest.get((i, j), z))  # its vertices are a voxel apart, under the grid's 1 mm
    over = set()
    for name, part in stage.parts.items():
        if stages.stem(part.file) in (*g.BONES, *sk.SHELLS):
            continue
        mesh = trimesh.load(part.file, force="mesh").apply_transform(head @ part.matrix)
        if mesh.bounds[1][2] < cap.bounds[0][2]:
            continue
        points = np.asarray(trimesh.sample.sample_surface(mesh, int(4 * mesh.area), seed=0)[0])
        points = points[points[:, 2] > cap.bounds[0][2]]
        squares = map(tuple, np.floor(points[:, :2]).astype(int))
        if any(z > lowest.get(ij, np.inf) for ij, z in zip(squares, points[:, 2], strict=True)):
            over.add(name)
    assert over == set()


def _poses():
    """{pose: {part: 4x4}}: the document at rest and at each servo's ends."""
    stage = stages.STAGES[skeleton.DOC]
    out = {"rest": {n: p.matrix for n, p in stage.parts.items()}}
    for horn, h in stage.horns.items():
        out |= {f"{horn} {deg:.0f}": stages.pose(stage, horn, deg).parts for deg in h.limits}
    return out


@pytest.mark.model
@pytest.mark.bones
@pytest.mark.parametrize("skull,cap", CAPS[1:])  # the worn pair: the bones the document carries
def test_the_skull_clears_the_mechanism_at_every_servo_end_with_its_calvaria_on(skull, cap):
    """#874's acceptance: at rest and at each servo's ends, the skull and its calvaria keep skeleton.CLEAR_MM, to the
    Finish's voxel, from every part of the mechanism that moves against them (whatever rides the head with them is
    let into the bone instead). Read on the bones' vertices, a voxel apart, and a part's points about 0.5 mm apart."""
    stage, poses = stages.STAGES[skeleton.DOC], _poses()
    carrier = stages.RIDES[f"{skull}:1"]
    rest = poses["rest"]
    still = {  # what never moves against the skull: its carrier and whatever rides with it
        n
        for n in stage.parts
        if all(
            np.allclose(np.linalg.inv(m[carrier]) @ m[n], np.linalg.inv(rest[carrier]) @ rest[n], atol=1e-6)
            for m in poses.values()
        )
    }
    moving = [
        n for n in stage.parts if n not in still and stages.stem(stage.parts[n].file) not in (*sk.SHELLS, *g.BONES)
    ]
    clouds = {}
    for n in moving:
        mesh = trimesh.load(stage.parts[n].file, force="mesh")
        clouds[n] = np.asarray(trimesh.sample.sample_surface(mesh, int(4 * mesh.area), seed=0)[0])
    near = []
    for stem in (skull, cap):
        bone = trimesh.load(stages.stl(stem), force="mesh")
        tree, (lo, hi) = cKDTree(bone.vertices), bone.bounds
        for pose, mats in poses.items():
            into = np.linalg.inv(mats[f"{stem}:1"])
            for n in moving:
                p = trimesh.transform_points(clouds[n], into @ mats[n])
                p = p[((p > lo - skeleton.CLEAR_MM) & (p < hi + skeleton.CLEAR_MM)).all(axis=1)]  # in the bone's box
                if len(p) and tree.query(p, distance_upper_bound=skeleton.CLEAR_MM)[0].min() < (
                    skeleton.CLEAR_MM - skeleton.PITCH
                ):
                    near.append((stem, n, pose, round(float(tree.query(p)[0].min()), 2)))
    assert near == []


@pytest.mark.model
@pytest.mark.bones
def test_the_skull_keeps_its_palate_through_the_gimbal_frames_windows():
    """#967: the skull's one piece (the test below) reaches under the gimbal frame's plate in front of it, between its
    windows: the palate, which the plate cut off before the maxillae rose through them (a piece that small is still
    kept, skeleton.KEEP, so losing it again shows there as a second piece)."""
    v = trimesh.load(stages.stl("skull"), force="mesh").vertices
    under = (v[:, 2] < gm.PLATE_Z[0]) & (v[:, 1] < gm.PLATE_Y[0]) & (np.abs(v[:, 0]) < gm.WINDOW_X)
    assert under.sum() > 1000


@pytest.mark.model
@pytest.mark.bones
@pytest.mark.parametrize("stem", g.BONES)
def test_each_bone_is_finished_into_one_piece_within_the_head(stem):
    """One piece (but crumbs of a voxel or two); a vertebra between the tilt axis and the Torso's lid. C3 too, since
    the neck stands on one tube up its canal (#1075): the printed rails cut its R transverse process off (#1060). The skull's
    palate holds on behind the R maxilla, between the gimbal frame's plate and the tie-bar's sweep, where the Finish
    seals the maxilla to the sphenoid (skeleton.SEAL). On the fit before #1035 it came off unsealed, a second piece of
    5.3 cm3; on this one it holds unsealed too (a thinner neck), so this check alone does not hold the seal (#874)."""
    mesh = trimesh.load(stages.stl(stem), force="mesh")
    pieces = [p for p in mesh.split(only_watertight=False) if abs(p.volume) > skeleton.PITCH**3 * 8]
    assert len(pieces) == 1
    if stem in g.NECK:
        lid = stages.STAGES[skeleton.DOC].parts["torso lid:1"]
        top = (
            trimesh.load(lid.file, force="mesh").apply_transform(lid.matrix).bounds[1][2]
            - stages.DOCS[skeleton.DOC]["eyes"][0][2]
        )
        assert top < mesh.bounds[0][2] and mesh.bounds[1][2] < nk.HEAD_AXES["tilt"][0][2]


@pytest.mark.model
@pytest.mark.bones
@pytest.mark.parametrize("side", list(nk.MANDIBLE_CHAIN))
@pytest.mark.xfail(strict=True, raises=AssertionError, reason=CHAIN)
def test_the_mandible_covers_the_jaw_carrier_from_outside(side):
    """#968: along each of the jaw's chains (model/printed/neck.py jaw_chains(), the condyle to the chin), straight
    outboard of the carrier, the finished mandible's bone lies against it (within a voxel: the carrier is let into the
    bone) and stands the print floor thick beyond it, to a voxel. Inboard the carrier may show: its post, and the
    chain where the ramus is thinner than it. nk.MANDIBLE_CHAIN is a copy of the scene's mandible: this holds it to
    the bone (ADR 0011)."""
    from model.printed import neck

    rng = np.random.default_rng(0)
    bone, jaw = (
        np.asarray(trimesh.sample.sample_surface(trimesh.load(stages.stl(stem), force="mesh"), 400_000, seed=rng)[0])
        for stem in ("mandible", "jaw")
    )
    sign = 1.0 if side == "L" else -1.0
    bare = []
    for a, b in itertools.pairwise(np.array(neck.jaw_chains()[side])):
        for t in (0.1, 0.3, 0.5, 0.7, 0.9):
            p = a + (b - a) * t
            # each surface's points straight outboard of the chain here, mm from it
            of_bone, of_jaw = (
                sign * (s[np.linalg.norm(s[:, 1:] - p[1:], axis=1) < 1.0, 0] - p[0]) for s in (bone, jaw)
            )
            face = of_jaw[
                (of_jaw > 0) & (of_jaw < 6.0)
            ].max()  # the carrier's own outboard face (not the other chain's)
            beyond = of_bone[of_bone > face - skeleton.PITCH]
            if not (
                len(beyond)
                and beyond.min() < face + skeleton.PITCH
                and beyond.max() - face >= skeleton.FLOOR - skeleton.PITCH
            ):
                bare.append((tuple(np.round(p, 1)), round(float(face), 2)))
    assert bare == []
