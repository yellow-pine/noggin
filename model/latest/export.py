"""In a candidate's own source tree (its parts just built without the Finish): its head's frame (head.json, which the
raw bones need alone), then its review's job at rest and its review's assemble step, written to the latest file's cache
(model/latest export()).

  PYTHONPATH=<src> python model/latest/export.py <assembled.blend> <morty.blend>

The job is the candidate's own review.job() with what assemble never reads left out: the plates and the motion past
its rest pose, the Exploded offsets, and the unfinished bones' meshes (a point stands in for their boxes)."""

import json
import os
import sys
import types

import numpy as np
import trimesh

out, morty = sys.argv[1:3]
os.environ["NOGGIN_MORTY"] = morty  # before the review reads it
from model import skeleton, stages  # noqa: E402 the candidate's, from PYTHONPATH

head = stages.align(*stages.DOCS[skeleton.DOC]["eyes"]).tolist()  # first: the raw bones need it alone
with open(os.path.join(os.path.dirname(out), "head.json"), "w") as f:
    json.dump({"head": head}, f)
from model import review  # noqa: E402
from model.render import pictures  # noqa: E402


def load(f, **kw):
    return trimesh.load(f, **kw) if os.path.exists(f) else trimesh.Trimesh([[0, 0, 0]] * 3, [[0, 1, 2]])


pictures.trimesh = types.SimpleNamespace(load=load, transform_points=trimesh.transform_points)
pictures.offsets = lambda doc, level: {n: np.zeros(3) for n in stages.STAGES[doc].parts}
review.plates = lambda stage: {}
review.motion = lambda stage, curves: [(1, {n: p.matrix for n, p in stage.parts.items()})]
job = review.job("coarse") | {"head": head}
path = out.replace("assembled-", "job-").removesuffix(".blend") + ".json"
with open(path, "w") as f:
    json.dump(job, f)
part = out.removesuffix(".blend") + ".tmp.blend"
review._blender([os.path.join(stages.REPO, review.skeleton.SCENE), "-P", review.SCRIPT, "--", path, part, "assemble"])
os.replace(part, out)
