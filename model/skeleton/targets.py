"""PROTOTYPE (#872, throwaway): the warp's landmark targets and the carve's keep-outs, read from the model (ADR 0011),
in the Stage 3 document's frame (mm, z up, -y forward), for model/skeleton/build.py. Run in the model venv:
`uv run python -m model.skeleton.targets model/build/skeleton/targets.json`."""

import json
import sys

import numpy as np

from model import base as nb
from model import electrical, envelopes, stages
from model import geometry as g
from model import gimbal as gm
from model import neck as nk

FRAME = np.array(stages.DOCS["next-mech-back"]["next-eyes"][0], float)  # the head's frame in the document's


def doc(p):
    return [round(float(c), 3) for c in np.asarray(p, float) + FRAME]


def main(out):
    (x0, x1), (y0, y1), (z0, _) = nb.TORSO
    floor = nk.MOUNT_Z[0]
    (oy0, oy1), (oz0, oz1) = nb.OPENING
    data = {
        "eyes": {s: doc(c) for s, c in gm.EYE.items()},
        "hinge": [doc((sx * sum(nk.JAW_X) / 2, *nk.JAW)) for sx in (1, -1)],  # the condyles' targets, L then R
        "tilt": doc((0.0, *nk.AXIS)),  # the pan axis meets the tilt axis here
        "post_r": nk.POST_R,
        "chin": doc((0.0, nk.CHIN_Y, nk.JAW_ARM_Z[0])),
        "floor": [doc((x0, y0, z0)), doc((x1, y1, floor))],  # the Torso's floor, the foot (kept)
        "lid_top": doc((0, 0, nb.TORSO[2][1]))[2],
        # the -x swap opening's door (y, z) outline, from the floor's top, roof at 45 deg to its peak
        "door": [
            doc((x0, y, floor + z))[1:]
            for y, z in ((oy0, oz0), (oy1, oz0), (oy1, oz1), ((oy0 + oy1) / 2, oz1 + (oy1 - oy0) / 2), (oy0, oz1))
        ],
        "door_x": doc((x0, 0, 0))[0],
        "usb": {n: [doc(lo), doc(hi)] for n, (lo, hi) in nb.openings().items()},
        # the palettes Cansin picked for the bust (#872): the Skin's "cansin", the Skeleton's "anatomical"
        "skin_palette": {k: v[3] for k, v in g.THEMES["Skin palette"]["cansin"].items()},
        "skeleton_palette": {k: v[3] for k, v in g.THEMES["Skeleton palette"]["anatomical"].items()},
        "groups": {n: grp for n, (grp, _) in g.PRINTED.items()},
        "petg_g_cm3": g.MATERIALS["PETG HF"]["density_g_cm3"],
        "servo": {k: envelopes.SERVO[k] for k in ("case", "tabs", "shaft", "tip_z", "spline_r", "boss_z")},
        # the 9 g servo on the Shields' 5 V rail (#861): each figure interpolated at the rail as main's model/sim.py
        # does; the rated one main's eyes/servo.py (#880, newer than this branch): 0.32 at 4.8 V, 0.4 at 6 V
        "servo_kgf_cm": {
            k: round(a[k] + (b[k] - a[k]) * (electrical.SERVO_RAIL_V - va) / (vb - va), 3)
            for (va, a), (vb, b) in [
                sorted(
                    (
                        {4.8: {"rated_kgfcm": 0.32}, 6.0: {"rated_kgfcm": 0.4}}
                        | {v: electrical.servo.SPEC[v] | {"rated_kgfcm": r} for v, r in ((4.8, 0.32), (6.0, 0.4))}
                    ).items()
                )
            ]
            for k in ("rated_kgfcm", "stall_kgfcm")
        },
    }
    with open(out, "w") as f:
        json.dump(data, f, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
