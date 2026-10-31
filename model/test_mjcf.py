import itertools

import mujoco
import numpy as np
import trimesh

from model import mjcf
from model.engine import stages


def test_eyes_document_loads_with_every_part_where_the_engine_puts_it():
    """The tracer (#147): every part of noggin-eyes is a MuJoCo body whose placement, after MuJoCo's own forward
    kinematics, puts its mesh's bounding-box corners within 0.1 mm of the old engine's pose at 0 degrees."""
    doc = stages.STAGES["noggin-eyes"]
    model = mjcf.model("noggin-eyes")
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    engine = stages.pose(doc, next(iter(doc.horns)), 0).parts
    assert {model.body(i).name for i in range(1, model.nbody)} == set(engine)
    for name, expected in engine.items():
        body = data.body(name)
        lo, hi = trimesh.load(doc.parts[name].file, force="mesh").bounds
        corners = np.array([[*c, 1.0] for c in itertools.product(*zip(lo, hi))])
        actual = corners[:, :3] @ body.xmat.reshape(3, 3).T + body.xpos * 1000  # metres in MuJoCo, mm in the engine
        worst = np.linalg.norm(actual - (corners @ expected.T)[:, :3], axis=1).max()
        assert worst < 0.1, (name, worst)
