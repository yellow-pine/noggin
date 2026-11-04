"""The hero (#117, #642): the Mech mid-conversation, an 8 s loop keyed by hand. The jaw talks in two phrases,
the head glances aside and back twice and nods while it listens. The head's keys are in head degrees (the pan and tilt
pivots' own), the jaw's in today's horn degrees from neutral, scaled to the jaw's open end; each turned into its
servo's degrees through the Mech's own four-bars (model/neck.py servo_for). Minimum-jerk between keys. Played by
MuJoCo (model/trajectories.py)."""

import numpy as np

from model import neck

SECONDS = 8.0


def talk(t, syllables):
    """Jaw keys for a phrase from t: each syllable opens to its depth (horn degrees, negative opens) and nearly closes,
    0.26 s each; shut at the end."""
    keys = [(t, 0.0)]
    for i, depth in enumerate(syllables):
        keys += [(t + 0.26 * i + 0.11, depth), (t + 0.26 * (i + 1), -4.0)]
    return keys[:-1] + [(keys[-1][0], 0.0)]


def glance(t, head, back):
    """Pan keys in head degrees of a glance from t and back at `back`: the head turns over 0.6 s and back."""
    return [(t + 0.04, 0.0), (t + 0.64, head), (back + 0.04, head), (back + 0.64, 0.0)]


MOUTH = [
    *talk(0.2, (-22, -34, -18, -30, -26, -15, -32, -20, -28, -16)),
    *talk(4.8, (-20, -30, -25, -35, -17, -28, -22, -15, -19, -14)),
    (8.0, 0.0),
]
HEAD = {  # servo: [(seconds, head degrees: the pan or tilt pivot's own, from rest)]
    "rotate": [(0.0, 0.0), *glance(1.5, 24.0, 2.75), *glance(5.6, -20.0, 7.2), (8.0, 0.0)],
    "tilt": [(0.0, 0.0), (3.3, 0.0), (3.7, 15.0), (4.0, 4.0), (4.3, 12.0), (4.75, 0.0), (8.0, 0.0)],  # + nods down
}


def _ease(f):
    return f**3 * (10 - 15 * f + 6 * f**2)  # minimum jerk


def _eased(keys, t):
    times = [k for k, _ in keys]
    i = min(max(np.searchsorted(times, t, side="right"), 1), len(keys) - 1)
    (t0, a), (t1, b) = keys[i - 1], keys[i]
    return a + (b - a) * _ease(min(1.0, max(0.0, (t - t0) / (t1 - t0))))


def keys_at(t):
    """The Mech's hero at t seconds (#642), {servo: horn degrees from neutral}: the head keys through its own
    four-bars (model/neck.py servo_for), the jaw's phrases scaled from the deepest syllable to the jaw's open end. The
    eyes stay still: the gestures move them."""
    deepest, wide = -min(d for _, d in MOUTH), max(neck.RANGES["jaw"])
    jaw = max(0.0, -_eased(MOUTH, t)) / deepest * wide
    out = {s: neck.servo_for(d, _eased(HEAD[s], t)) for s, d in (("rotate", "pan"), ("tilt", "tilt"))}
    return {s: round(d, 2) for s, d in (out | {"mouth": neck.servo_for("jaw", jaw)}).items()}
