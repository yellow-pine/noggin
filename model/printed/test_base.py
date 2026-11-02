"""Seam: the next Mech's base and its Base candidates' board carriers (model/printed/base.py) as model/stages.py places
them at rest with the neck and the gimbal: (a)'s overlap nothing; (b)'s tower meets the head's middle and nothing else."""

import itertools

import pytest

from model import stages
from model.printed.test_gimbal import _overlaps
from model.printed.test_neck import _shape

PLUGGED = {frozenset((f"next Core {n}:1", f"next Shield {n}:1")) for n in (1, 2)}  # each Core in its Shield's header
BASE = ("next base plate", "next pack", "next board", "next Core", "next Shield", "next switch board")


def _hits(doc):
    """{frozenset(pair)} of the parts overlapping at rest where one is the base's or the boards'."""
    shapes = {n: _shape(p) for n, p in stages.STAGES[doc].parts.items()}
    return {
        frozenset((a, b))
        for a, b in itertools.combinations(shapes, 2)
        if (a.startswith(BASE) or b.startswith(BASE))
        and frozenset((a, b)) not in PLUGGED
        and _overlaps(shapes[a], shapes[b]) > 0.01
    }


@pytest.mark.build
def test_candidate_a_overlaps_nothing_at_rest():
    assert _hits("next-mech-a") == set()


@pytest.mark.build
def test_candidate_bs_tower_meets_the_neck_and_gimbal_on_the_pan_axis_and_nothing_else():
    """The pan yoke's disc, the head mount, the gimbal frame's plate, the tie-bar and the yaw servo with its horn all sit
    on the pan axis (model/base.py)."""
    middle = (
        "next pan yoke",
        "next head mount",
        "next gimbal frame",
        "next tie-bar",
        "next yaw servo",
        "next yaw horn",
    )
    assert _hits("next-mech-b") == {frozenset(("next board tower:1", f"{n}:1")) for n in middle}
