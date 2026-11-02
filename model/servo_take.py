"""A filmed Take -> the take file model/servo_fit.py reads (#644, docs/build/tests.md "Filming a servo").

The horn carries a printed ArUco marker (OpenCV's fiducial: its corners give its turn in the picture, wherever the
shaft is); OpenCV reads its angle at each frame of the slow-motion clip, at the frame's own time. The servo runs the
Core's `take` (eyes.TAKE), whose writes are on the Core's clock, and nothing in the kit shows when the Core writes: the
take puts them where the filmed horn's opening ramp lags them as the model's servo does at mjcf.SERVO. On the ramp, a
degree a frame, the horn lags alike under any load, so a servo's Takes share one clock, its offset from the Core's
taken in by the fitted delay (docs/adr/0018).

`python -m model.servo_take marker > marker.svg`: the marker to print, 12 mm across.
`python -m model.servo_take A.mov <load g> <arm mm>`: writes A.json beside the clip."""

import json
import math
import os
import sys

import cv2
import numpy as np

from model import mjcf, servo_fit, traces

MARKER = cv2.aruco.DICT_4X4_50  # marker 0
REST_S = 0.2  # the clip opens on the horn at rest at centre for at least this long
LEAD_S, TAIL_S = 0.25, 1.0  # the frames kept before the take's first write and after its last

TAKE = [(ms, deg - traces.mod.EYE_CENTER) for ms, deg in traces.mod.TAKE]
_RAMP_END = int(np.argmax(np.abs(np.diff([d for _, d in TAKE])) > 1))  # the ramp's last write, before the first step
RAMP_DEG, STEP_S = TAKE[_RAMP_END][1], TAKE[_RAMP_END + 1][0] / 1000
LEVELS = RAMP_DEG * np.linspace(0.2, 0.8, 13)  # on the ramp, clear of its start and its end


def commands():
    """[[s, degrees from neutral]] the Core writes to the right eye (Shield port 4) through `take`, from 0."""
    log, _ = traces.writes("take")
    held = {ms: a for ms, servo, a in log if servo == "r_eye" and ms >= 0}  # the last write of each instant
    return [[ms / 1000, a] for ms, a in sorted(held.items())]


def angles(video):
    """(t_s, degrees) of marker 0 at each frame it is seen: the clip's frame times and its turn, counter-clockwise as
    seen, unwrapped."""
    clip = cv2.VideoCapture(video)
    refine = cv2.aruco.DetectorParameters()
    refine.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX  # a pixel off on a 60 px edge is a degree
    detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(MARKER), refine)
    t, deg = [], []
    while (frame := clip.read())[0]:
        corners, ids, _ = detector.detectMarkers(frame[1])
        if ids is not None and 0 in ids:
            c = corners[list(ids.flatten()).index(0)][0]  # top left, top right, bottom right, bottom left
            dx, dy = c[1] + c[2] - c[0] - c[3]  # its top and bottom edges, left to right
            t.append(clip.get(cv2.CAP_PROP_POS_MSEC) / 1000)
            deg.append(math.atan2(-dy, dx))  # the picture's y runs down
    assert t, f"marker 0 not seen in {video}"
    return np.array(t), np.degrees(np.unwrap(deg))


def _crossings(t, deg):
    """When deg first reaches each of LEVELS, between frames."""
    i = np.array([np.argmax(deg >= level) for level in LEVELS])
    assert (i > 0).all(), "the opening ramp is not in the clip: start filming before `noggin take`, the marker in frame"
    return t[i - 1] + (LEVELS - deg[i - 1]) * (t[i] - t[i - 1]) / (deg[i] - deg[i - 1])


def take(t_s, marker_deg, load_g, arm_mm):
    """The take of a clip whose marker turned through marker_deg at t_s, the Core's writes put where the opening ramp
    lags them as the model's servo does."""
    t, deg = np.asarray(t_s), np.asarray(marker_deg)
    deg = deg - np.median(deg[t < t[0] + REST_S])
    deg *= np.sign(deg[np.argmax(np.abs(deg) > RAMP_DEG / 2)]) * np.sign(RAMP_DEG)  # the marker turns as commanded
    writes = commands()
    ramp = [w for w in writes if w[0] < STEP_S]
    model = {"load_g": load_g, "arm_mm": arm_mm, "t_s": np.arange(0, STEP_S, 0.0005).tolist(), "command": ramp}
    t0 = float(np.mean(_crossings(t, deg) - _crossings(*servo_fit.play(mjcf.SERVO, model))))
    keep = (t >= t0 - LEAD_S) & (t <= t0 + writes[-1][0] + TAIL_S)
    assert t[keep][0] < t0, "the clip starts after the take: start filming first"
    t_kept = t[keep].tolist()
    command = [[t_kept[0], 0], *([t0 + s, a] for s, a in writes)]
    return {"load_g": load_g, "arm_mm": arm_mm, "t_s": t_kept, "horn_deg": deg[keep].tolist(), "command": command}


def svg(mm=12):
    """Marker 0 as an SVG of its true size, mm across, a cell of white around it."""
    black = cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(MARKER), 0, 6) == 0  # 6 cells, border too
    c = mm / 6
    cells = "".join(
        f'<rect x="{x * c:g}" y="{y * c:g}" width="{c:g}" height="{c:g}"/>' for y, x in zip(*black.nonzero())
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{mm + 2 * c:g}mm" height="{mm + 2 * c:g}mm" '
        f'viewBox="{-c:g} {-c:g} {mm + 2 * c:g} {mm + 2 * c:g}"><rect x="{-c:g}" y="{-c:g}" width="100%" '
        f'height="100%" fill="white"/>{cells}</svg>'
    )


if __name__ == "__main__":
    if sys.argv[1:] == ["marker"]:
        print(svg())
        sys.exit()
    assert len(sys.argv) == 4, "usage: python -m model.servo_take marker | clip.mov <load g> <arm mm>"
    clip, load_g, arm_mm = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    with open(os.path.splitext(clip)[0] + ".json", "w") as f:
        json.dump(take(*angles(clip), load_g, arm_mm), f)
