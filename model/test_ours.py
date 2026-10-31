"""Seam: `make stl` and `make step` (model/ours.py): a printed part's STL is watertight and in the designer's frame and
box, its STEP is a valid solid with the same box, and a Stage's STEP is valid, holds every part the engine places, and
spans the Stage's box at neutral, within 1 mm. Boxes: the designer's (model/printed/test_pupil.py, test_eye_bracket.py,
test_base_plate.py)."""

import cadquery as cq
import trimesh

from model import ours

BOX_MM = 1.0
PUPIL = (50.17, -8.83, -20.49, 67.83, 8.83, -18.5)
BRACKET = (-28.0, -45.6, -4.0, 87.0, 8.5, 18.0)
EYEBALL_L = (-20.5, -20.5, -18.5, 20.5, 20.28, 5.0)  # a sphere: OCCT leaves zero-area facets at its pole
# The base plate's x +-60 and y 135 (it sits at the PT origin), its bottom and the bracket stem's at z -2 (geometry.STEM_AT),
# and, read off this export once (regression values), the eyeballs' front at y -36 and the lids' top at z 67.6 (62.6
# until #147 lifted the eyes 5 mm onto the rail).
STAGE1 = (-60.0, -36.0, -2.0, 60.0, 135.0, 67.6)


def near(got, want):
    return max(abs(a - b) for a, b in zip(got, want)) <= BOX_MM


def box(shape):
    b = shape.BoundingBox()
    return b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax


def test_a_printed_parts_stl_is_watertight_in_its_designers_box(tmp_path):
    for stem, want in (("pupil", PUPIL), ("eye bracket", BRACKET), ("L eyeball", EYEBALL_L)):
        mesh = trimesh.load(ours.printable(stem, str(tmp_path / f"{stem}.stl")), force="mesh")
        assert mesh.is_watertight and mesh.volume > 0, stem
        assert near(mesh.bounds.flatten(), want), (stem, mesh.bounds)


def test_a_printed_parts_step_is_one_valid_solid_in_its_designers_box(tmp_path):
    shape = cq.importers.importStep(ours.export("eye bracket", str(tmp_path / "bracket.step"))).val()
    assert shape.isValid() and len(shape.Solids()) == 1
    assert near(box(shape), BRACKET), box(shape)


def test_a_stages_step_holds_every_placed_part_at_neutral(tmp_path):
    shape = cq.importers.importStep(ours.stage_step("noggin-stage1", str(tmp_path / "stage1.step"))).val()
    assert shape.isValid() and len(shape.Solids()) == 31  # the parts Stage 1 places: base, eyes, servos, boards, pack
    assert near(box(shape), STAGE1), box(shape)
