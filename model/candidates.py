"""The Mech's head variants (#686; their numbers and ranking: model/base.py): each one's figures for the sim report
(report(), model/report.py), which rank() orders. Back's boards sit where the cranium has room (#858): no parameter is
left to optimise."""

from model import base, stages
from model import geometry as g


def report(doc):
    """The variant's figures for rank() from its document (model/report.py): the parts beside the neck and the gimbal
    (the Torso, the pack, the carriers and the boards) and how many are printed, and the leads crossing pan and
    tilt."""
    stage = stages.STAGES[doc]
    parts = [
        n
        for sub in g.MECH[doc]
        if sub not in ("neck", "jaw", "eyes", *g.SKINS.values())
        for n in stages.SUBS[sub]().parts
    ]
    return {
        "parts": parts,
        "printed": sum(stages.stem(stage.parts[n].file) in g.PRINTED for n in parts),
        "leads": base.leads(stage),
    }
