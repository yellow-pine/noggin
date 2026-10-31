"""Measured Mech geometry as data (mm, degrees). Source: docs/research/2026-10-31-twin.md.
Eyes frame: L eye centre at origin, +Y up, -Z front. PT frame: Z up, pan axis through (0,0).
Pure Python, no imports: scripts/fusion_run.py inlines this file into Fusion scripts.
"""

EYE_L = (0.0, 0.0, 0.0)
EYE_R = (59.0, 0.0, 0.0)
CENTRE_X = 29.5


def eyes_to_pt(p):
    x, y, z = p
    return (29.5 - x, z - 28.5, y + 81.5)


def pt_to_eyes(p):
    x, y, z = p
    return (29.5 - x, z - 81.5, y + 28.5)
