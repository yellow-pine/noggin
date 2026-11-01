"""The README hero (#117): stage 3 mid-conversation, an 8 s loop keyed by hand. The jaw talks in two phrases, the
head glances aside and back twice and nods while it listens, the eyes lead each glance with a saccade and settle back
as the head arrives, the lids drop with the nod and blink. Timing follows the Core program (eyes/eyes.py): a blink
lifts, closes over 160 ms, holds 80 ms, reopens past the level over 240 ms and settles (#258); a saccade is one step. The head moves as far as the
designer's (about 25 degrees of pan, 15 of nod, near the horn limits): its keys are in head degrees (the pan and tilt
pivots' own), converted to horn degrees through the four-bar kinematics (model/stages.py pose); every other key is in model horn degrees
from neutral inside geometry.LIMITS (a blink shuts the lids at -30.75, where they meet: model/lids.py).
Minimum-jerk between keys.
Rendered by model/render/pictures.py (`make hero`)."""

import functools

import numpy as np

from model import geometry as g
from model import stages

FPS, SECONDS = 10, 8.0  # 100 ms frames, as the gesture GIFs (12.5 fps went over 3 MB)
STAGE = stages.STAGES["noggin-stage3"]
LID_OPEN, LID_DOWN = 8.0, -4.0  # lid horn: talking, in the nod
LID_SHUT = g.HORN_LIMITS["l_lid"][0] - 90  # shut in a blink: the lips meet at the lid limit


def blink(t, lid=LID_OPEN):
    """Lid keys for a blink starting at t (eyes/eyes.py Eyes.blink), its lift and overshoot 2 horn degrees."""
    return [
        (t, lid),
        (t + 0.04, lid + 2),
        (t + 0.2, LID_SHUT),
        (t + 0.28, LID_SHUT),
        (t + 0.52, lid + 2),
        (t + 0.62, lid),
    ]


def talk(t, syllables):
    """Jaw keys for a phrase from t: each syllable opens to its depth (horn degrees, negative opens) and nearly closes,
    0.26 s each; shut at the end."""
    keys = [(t, 0.0)]
    for i, depth in enumerate(syllables):
        keys += [(t + 0.26 * i + 0.11, depth), (t + 0.26 * (i + 1), -4.0)]
    return keys[:-1] + [(keys[-1][0], 0.0)]


def glance(t, eyes, head, back):
    """(eye keys, pan keys in head degrees) of a glance from t and back at `back`: the eyes jump ahead in one step,
    the head follows over 0.6 s while the eyes ease back toward centre (eye and head degrees of one sign turn one way)."""
    eye = [(t, 0.0), (t + 0.08, eyes), (t + 0.68, eyes / 3), (back, eyes / 3), (back + 0.08, 0.0)]
    pan = [(t + 0.04, 0.0), (t + 0.64, head), (back + 0.04, head), (back + 0.64, 0.0)]
    return eye, pan


EYE_1, PAN_1 = glance(1.5, 15.0, 24.0, 2.75)
EYE_2, PAN_2 = glance(5.6, -14.0, -20.0, 7.2)
LIDS = [(0.0, LID_OPEN), *blink(0.9), *blink(2.75), (3.7, LID_DOWN), (4.3, LID_OPEN), *blink(5.6)]
KEYS = {  # servo (geometry.LIMITS keys): [(seconds, model horn degrees from neutral)]
    "l_lid": [*LIDS, *blink(7.2), (8.0, LID_OPEN)],
    "l_eye": [(0.0, 0.0), *EYE_1, *EYE_2, (8.0, 0.0)],
    "mouth": [
        *talk(0.2, (-22, -34, -18, -30, -26, -15, -32, -20, -28, -16)),
        *talk(4.8, (-20, -30, -25, -35, -17, -28, -22, -15, -19, -14)),
        (8.0, 0.0),
    ],
}
KEYS["r_lid"], KEYS["r_eye"] = KEYS["l_lid"], KEYS["l_eye"]
HEAD = {  # servo: [(seconds, head degrees: the pan or tilt pivot's own, from rest)]
    "rotate": [(0.0, 0.0), *PAN_1, *PAN_2, (8.0, 0.0)],
    "tilt": [(0.0, 0.0), (3.3, 0.0), (3.7, 15.0), (4.0, 4.0), (4.3, 12.0), (4.75, 0.0), (8.0, 0.0)],  # + nods down
}
NECK = {"rotate": "pan horn", "tilt": "tilt horn"}


def _ease(f):
    return f**3 * (10 - 15 * f + 6 * f**2)  # minimum jerk


def _eased(keys, t):
    times = [k for k, _ in keys]
    i = min(max(np.searchsorted(times, t, side="right"), 1), len(keys) - 1)
    (t0, a), (t1, b) = keys[i - 1], keys[i]
    return a + (b - a) * _ease(min(1.0, max(0.0, (t - t0) / (t1 - t0))))


@functools.cache
def _head_table(servo):
    """(head degrees, horn degrees), head ascending: the four-bar kinematics over the horn's limits, on the branch
    from the lower limit where the head still turns (the pan's head stops turning past horn +60)."""
    horn = NECK[servo]
    lo, hi = g.HORN_LIMITS[servo]
    horns = np.arange(lo - 90, hi - 90 + 0.25, 0.5)
    head = np.array([stages.pose(STAGE, horn, d).joints[horn.replace("horn", "pivot")] for d in horns])
    turn = np.sign(np.diff(head))
    n = len(turn) if (turn == turn[0]).all() else int(np.argmax(turn != turn[0]))
    head, horns = head[: n + 1], horns[: n + 1]
    return (head, horns) if turn[0] > 0 else (head[::-1], horns[::-1])


def horn_of(servo, head_deg):
    """The pan or tilt horn degrees that turn the head head_deg (its pivot's degrees from rest)."""
    head, horns = _head_table(servo)
    assert head[0] <= head_deg <= head[-1], (servo, head_deg)
    return float(np.interp(head_deg, head, horns))


def at(t):
    """The pose at t seconds: {servo: model horn degrees from neutral}."""
    out = {servo: round(_eased(keys, t), 2) for servo, keys in KEYS.items()}
    return out | {servo: round(horn_of(servo, _eased(keys, t)), 2) for servo, keys in HEAD.items()}


def frames():
    return [at(i / FPS) for i in range(round(SECONDS * FPS))]
