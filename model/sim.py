"""The servo's numbers the model reads: its rated torque (model/mujoco_report.py holds each servo to it)."""

from model import electrical

# The 9 g servo's rating on the Shield's 5 V rail, which feeds every servo (#861): the vendor's spec sheet rates it
# at 4.8 V and 6 V (eyes/servo.py, docs/research/2026-10-31-electrical.md Clutch), interpolated linearly at the rail,
# inferred: 0.33 kgf.cm.
(_v0, _s0), (_v1, _s1) = sorted(electrical.servo.SPEC.items())
RATED_KGF_CM = round(
    _s0["rated_kgfcm"] + (_s1["rated_kgfcm"] - _s0["rated_kgfcm"]) * (electrical.SERVO_RAIL_V - _v0) / (_v1 - _v0),
    2,
)
