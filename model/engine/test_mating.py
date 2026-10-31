"""Seam: the mating check's result per joint, as `make sim` writes it into the reports (model/engine/mating.py). Local
only: the features are measured on the designer's meshes (docs/references, model/build/steps)."""

import functools

import numpy as np
import pytest

from model import geometry as g
from model.engine import mating, meshes, stages

HAVE_REFERENCES = stages.os.path.isdir(stages.MODELS["eyes"]) and stages.os.path.isfile(stages.step("horn"))
pytestmark = pytest.mark.skipif(not HAVE_REFERENCES, reason="local references only")


@functools.cache
def loaded(doc):
    return meshes.load(stages.STAGES[doc])


def check(doc, parts=None):
    stage = stages.STAGES[doc]
    stage = stage._replace(parts={**stage.parts, **(parts or {})})
    placed = {n: meshes.Placed(m, stage.parts[n].matrix) for n, m in loaded(doc).items()}
    return {m["joint"]: m for m in mating.check(stage, placed)}


def test_every_joint_is_checked_in_some_document():
    seen = {j for doc in ("noggin-eyes", "noggin-pan-tilt", "noggin-mouth") for j in check(doc)}
    assert {name for name, _ in mating.JOINTS} <= seen


def test_a_servo_moved_0_3_mm_off_its_lug_fails_its_screws_and_nothing_else():
    stage = stages.STAGES["noggin-mouth"]
    servo = stage.parts["jaw servo:1"]
    moved = servo._replace(matrix=stages.translate((0, 0.3, 0)) @ servo.matrix)
    before, after = check("noggin-mouth"), check("noggin-mouth", {"jaw servo:1": moved})
    changed = {j for j in after if after[j]["ok"] != before[j]["ok"]}
    assert changed == {
        "jaw servo / jaws servo mount near tab screw",
        "jaw servo / jaws servo mount far tab screw",
        "jaw horn on the jaw servo spline",
    }
    assert np.isclose(after["jaw servo / jaws servo mount near tab screw"]["mm"], 0.3, atol=0.01)


def test_a_servo_pushed_into_its_mount_overlaps_it():
    stage = stages.STAGES["noggin-mouth"]
    servo = stage.parts["jaw servo:1"]
    moved = servo._replace(matrix=stages.translate((1.0, 0, 0)) @ servo.matrix)  # the tab 1 mm into the lug (x 73.42)
    seat = check("noggin-mouth", {"jaw servo:1": moved})["jaw servo in its mount"]
    assert not seat["ok"] and seat["mm"] > 0.5 and seat["parts"] == ["jaw servo:1", "jaws servo mount:1"]


def test_with_the_pan_mounts_where_the_stl_has_them_the_pan_lead_runs_into_the_plain_mount():
    stage = stages.STAGES["noggin-pan-tilt"]
    back = {
        n: stage.parts[n]._replace(matrix=stages.translate((0, dy, 0)) @ stage.parts[n].matrix)
        for n, dy in (("servo mount plain:1", -g.MOUNT_SWAP_Y), ("servo mount cutout:1", g.MOUNT_SWAP_Y))
    }
    assert check("noggin-pan-tilt")["pan servo lead exit"]["ok"]
    lead = check("noggin-pan-tilt", back)["pan servo lead exit"]
    assert not lead["ok"] and lead["parts"] == ["pan servo:1", "servo mount plain:1"]
