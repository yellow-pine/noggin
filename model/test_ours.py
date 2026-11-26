"""Seam: `just stl` and `just step` (model/ours.py): a printed part's STL is watertight in its shape's box, its STEP is a
valid solid with the same box, and a document's STEP is valid and holds every part model/stages.py places but the
skull's mesh bones (geometry.BONES), the Torso's foot on z 0."""

import cadquery as cq
import pytest
import trimesh

from model import geometry, ours, printed, stages

BOX_MM = 1.0
DOC = next(iter(geometry.MECH))


def near(got, want):
    return max(abs(a - b) for a, b in zip(got, want)) <= BOX_MM


def box(shape):
    b = shape.BoundingBox()
    return b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax


def test_a_printed_parts_stl_is_watertight_in_its_shapes_box(tmp_path):
    for stem in ("pitch bar", "L eyeball cap"):
        mesh = trimesh.load(ours.printable(stem, str(tmp_path / f"{stem}.stl")), force="mesh")
        assert mesh.is_watertight and mesh.volume > 0, stem
        assert near(mesh.bounds.flatten(), box(ours.SHAPES[stem]().val())), (stem, mesh.bounds)


def test_just_stl_prints_the_clearance_coupon_watertight_flat_on_the_bed(tmp_path):
    """#624: a Coupon prints from `just stl` beside the parts, but is no part of the Mech."""
    assert "clearance coupon" in ours.PRINTS and "clearance coupon" not in printed.PARTS
    mesh = trimesh.load(ours.printable("clearance coupon", str(tmp_path / "coupon.stl")), force="mesh")
    assert mesh.is_watertight and mesh.volume > 0 and mesh.bounds[0][2] == 0


@pytest.mark.parametrize("stem", ["pitch bar", "cranium tray"])
def test_a_printed_parts_step_is_one_valid_solid_in_its_shapes_box(tmp_path, stem):
    shape = cq.importers.importStep(ours.export(stem, str(tmp_path / "part.step"))).val()
    assert shape.isValid() and len(shape.Solids()) == 1
    assert near(box(shape), box(ours.SHAPES[stem]().val())), box(shape)


@pytest.fixture
def doc_step(tmp_path):
    """The document's STEP, every part built and written in setup: CI's 15 s times the test alone."""
    return ours.stage_step(DOC, str(tmp_path / "doc.step"))


@pytest.mark.model
def test_a_documents_step_holds_every_placed_part_at_neutral(doc_step):
    """Read back, each part is one valid solid, in the order model/stages.py places them, so an invalid one names
    itself (Linux's OCCT reads some B-spline solids back invalid where macOS's does not: #837, #851)."""
    shape = cq.importers.importStep(doc_step).val()
    names = [n for n, p in stages.STAGES[DOC].parts.items() if stages.stem(p.file) not in geometry.BONES]  # meshes
    assert len(shape.Solids()) == len(names)
    assert [n for n, s in zip(names, shape.Solids(), strict=True) if not s.isValid()] == []
    assert shape.isValid()
    assert abs(box(shape)[2]) < 1e-6  # the Torso's foot (base.TORSO)
