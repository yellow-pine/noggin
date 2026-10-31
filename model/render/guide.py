"""Guide sheets (#68): each step of PurpleShark's three assembly guides beside the model, rendered in Blender from that
step's camera (matched by eye) with only that step's parts. One contact sheet per guide in model/build/pictures/guide,
a row per step: the guide page, its picture, the model. Usage: python -m model.render.guide   (`make guide-sheets`)"""

import os
import subprocess
from collections import namedtuple

import numpy as np

from model import geometry as g
from model.engine import stages
from model.render import camera, pictures

OUT = os.path.join(pictures.OUT, "guide")
GUIDES = {  # guide: (its PDF under docs/references, the Stage document its steps are rendered in)
    "eyes": ("01-eyes/guide-eye-mech-instructions-final-v1.pdf", "noggin-stage1"),
    "pan-tilt": ("02-pan-tilt/guide-eye-mech-pan-and-tilt-instructions-release-v2.pdf", "noggin-stage2"),
    "mouth": ("03-mouth/guide-eye-mech-mouth-instructions-final-v1.pdf", "noggin-stage3"),
}
# page: 1-based PDF page; image: index of the picture among that page's embedded images; parts: what the picture shows;
# view: (azimuth, elevation) degrees of the camera in the PT frame, azimuth 0 in front of the Mech (-Y), 90 at its left
# (+X); lens: mm, None for the guide's orthographic-looking CAD views; fit: the parts a close-up frames (default: all)
Step = namedtuple("Step", "guide page image step parts view lens fit", defaults=(50, None))

BASE = ["PandT base:1"]
BOARDS1 = [
    "battery 1:1",
    "switch board 1:1",
    "receiver shield 1:1",
    "Core 1:1",
    "cable holder:1",
]
L_SIDE = ["L servo bracket:1", "L lid servo:1", "L eye servo:1"]
R_SIDE = ["R servo bracket:1", "R lid servo:1", "R eye servo:1"]
BRACKET = ["main bracket v2:1", *L_SIDE, *R_SIDE]
LIDS = ["L outside lid:1", "R outside lid:1"]
TOPLIDS = ["L inside lid:1", "R inside lid:1"]
CRANKS = ["L eyelid bar crank:1", "R eyelid bar crank:1"]
BARS = ["L eyelid bar:1", "R eyelid bar:1"]
BALLS = ["L eyeball:1", "R eyeball:1", "L pupil:1", "R pupil:1"]
EYE_LINKS = ["L eyeball bar:1", "R eyeball bar:1", "L eye horn:1", "R eye horn:1"]
LID_HORNS = ["L lid horn:1", "R lid horn:1"]
EYES = [*BRACKET, *LIDS, *TOPLIDS, *CRANKS, *BARS, *BALLS, *EYE_LINKS, *LID_HORNS]
PAN = ["bearing block:1", "pan base:1", "upright v2:1"]
BOARDS2 = ["receiver shield 2:1", "Core 2:1", "wire holder:1"]
SERVOS2 = ["tilt servo:1", "pan servo:1", "servo mount plain:1", "servo mount cutout:1"]
LINKS2 = ["tilt arm:1", "tilt horn:1", "tilt bar:1", "pan horn:1", "pan bar:1"]
STACK = [*PAN, *BOARDS2, *SERVOS2, *LINKS2]
JAW_SERVO = ["jaws servo mount:1", "jaw servo:1"]
MOUTH = [*JAW_SERVO, "top jaw:1", "bottom jaw:1", "jaw horn:1", "connector bar:1"]

STEPS = [
    Step("eyes", 13, 0, "2", [*BASE, "cable holder:1"], (180, 50)),
    Step("eyes", 13, 1, "3", [*BASE, *BOARDS1[:2], "cable holder:1"], (180, 50)),
    Step("eyes", 14, 0, "4", [*BASE, *BOARDS1], (180, 50)),
    Step("eyes", 16, 1, "6", L_SIDE, (135, 30)),
    Step("eyes", 17, 0, "7", ["main bracket v2:1", *L_SIDE], (150, -40)),
    Step("eyes", 19, 1, "9", [*BASE, *BOARDS1, *BRACKET], (0, 20), fit=BRACKET),
    Step("eyes", 20, 1, "10", [*BASE, *BOARDS1, *BRACKET, *LIDS], (-60, 55), fit=[*BRACKET, *LIDS, "battery 1:1"]),
    Step("eyes", 21, 1, "11", [*BASE, *BOARDS1, *BRACKET, *LIDS, *TOPLIDS], (-100, 60), fit=[*BRACKET, *LIDS]),
    Step(
        "eyes",
        22,
        1,
        "12",
        [*BASE, *BOARDS1, *BRACKET, *LIDS, *TOPLIDS, *CRANKS],
        (90, 10),
        fit=[*L_SIDE, CRANKS[0], LIDS[0], TOPLIDS[0]],
    ),
    Step(
        "eyes",
        23,
        1,
        "13",
        [*BASE, *BOARDS1, *BRACKET, *LIDS, *TOPLIDS, *CRANKS, *BARS],
        (-90, 15),
        fit=[*R_SIDE, CRANKS[1], BARS[1], LIDS[1]],
    ),
    Step(
        "eyes",
        25,
        1,
        "15",
        [*BASE, *BOARDS1, *BRACKET, *LIDS, *TOPLIDS, *CRANKS, *BARS, *BALLS],
        (-90, 15),
        fit=[*R_SIDE, BARS[1], BALLS[1]],
    ),
    Step("eyes", 28, 0, "18", [*BASE, *BOARDS1, *EYES[:-2]], (165, 45), fit=[*BRACKET, *BALLS, *EYE_LINKS]),
    Step("eyes", 29, 0, "19", [*BASE, *BOARDS1, *EYES], (180, 55), fit=EYES),
    Step("eyes", 32, 0, "23", [*BASE, *BOARDS1, *EYES], (90, 15), fit=[*L_SIDE, "L eyeball:1", CRANKS[0], BARS[0]]),
    Step("eyes", 37, 0, "built", [*BASE, *BOARDS1, *EYES], (0, 60)),
    Step("eyes", 37, 3, "built", [*BASE, *BOARDS1, *EYES], (-140, 50)),
    Step("pan-tilt", 7, 0, "CAD", [*BASE, *STACK], (60, 60), None),
    Step("pan-tilt", 7, 1, "CAD", [*BASE, *STACK], (-60, 35), None, fit=[*PAN, *SERVOS2, *LINKS2]),
    Step("pan-tilt", 13, 1, "4", PAN[1:], (150, 30)),
    Step("pan-tilt", 14, 1, "5-6", [*BASE, *PAN], (150, 40), fit=PAN),
    Step("pan-tilt", 15, 1, "7-8", [*BASE, *PAN, *BOARDS2, "tilt servo:1"], (30, 45)),
    Step("pan-tilt", 16, 1, "9", [*BASE, *PAN, *BOARDS2, *SERVOS2], (180, 50)),
    Step("pan-tilt", 18, 1, "11", [*BASE, *PAN, *BOARDS2, *SERVOS2, "tilt arm:1"], (-60, 30), fit=[*PAN, "tilt arm:1"]),
    Step("pan-tilt", 23, 1, "18", [*BASE, *BOARDS1, *STACK, *EYES], (180, 55)),
    Step("pan-tilt", 26, 3, "built", [*BASE, *BOARDS1, *STACK, *EYES], (0, 10), fit=[*PAN, "tilt arm:1", *LIDS]),
    Step("mouth", 10, 0, "4", ["main bracket v2:1", *JAW_SERVO], (180, 0)),
    Step("mouth", 11, 1, "6", [*EYES, *JAW_SERVO, "top jaw:1"], (-10, 20), fit=["main bracket v2:1", "top jaw:1"]),
    Step(
        "mouth",
        12,
        0,
        "7",
        [*BASE, *STACK, *EYES, *JAW_SERVO, "top jaw:1", "bottom jaw:1"],
        (-75, 15),
        fit=["main bracket v2:1", *JAW_SERVO, "top jaw:1", "bottom jaw:1"],
    ),
    Step("mouth", 13, 0, "8-9", [*BASE, *STACK, *EYES, *MOUTH], (-90, 10), fit=MOUTH),
    Step("mouth", 13, 1, "built", [*BASE, *BOARDS1, *STACK, *EYES, *MOUTH], (-25, 25)),
    Step("mouth", 14, 0, "CAD", ["main bracket v2:1", *MOUTH], (-30, 30), None),
    Step("mouth", 14, 1, "CAD", [*BASE, *STACK, *BRACKET, *MOUTH], (-30, 35), None),
]
RENDER, CELL, MARGIN = (800, 600), (860, 600), 1.1


def pdf(name):
    return os.path.join(stages.REF, GUIDES[name][0])


def view_dir(az, el):
    a, e = np.radians(az), np.radians(el)
    return np.cos(e) * np.array([np.sin(a), -np.cos(a), 0]) + np.sin(e) * np.array(g.Z)


def sheet(name):
    """Render the guide's steps in one Blender job, cut each step's page and picture out of the PDF, tile the sheet."""
    doc = GUIDES[name][1]
    steps = [s for s in STEPS if s.guide == name]
    folder = os.path.join(OUT, name)
    os.makedirs(folder, exist_ok=True)
    for old in os.listdir(folder):
        os.remove(os.path.join(folder, old))
    stage, manifest, hulls = pictures.prepare(doc, g.STAGES[doc])
    mats = pictures.metres({n: p.matrix for n, p in stage.parts.items()})
    shots, cells = [], []
    for i, s in enumerate(steps):
        shown = {n: mats[n] for n in s.parts}  # parts left out of a shot's pose are hidden (blender.py)
        pts = pictures.points(hulls, shown, s.fit)
        cam = camera.fit(pts, view_dir(*s.view), g.Z, RENDER[0] / RENDER[1], s.lens, MARGIN)
        shots.append(pictures.shot(os.path.join(folder, f"{i:02d}-model.png"), RENDER, cam, shown))
        page, photo = (os.path.join(folder, f"{i:02d}-{k}") for k in ("page", "photo"))
        subprocess.run(
            ["pdftoppm", "-f", str(s.page), "-l", str(s.page), "-r", "72", "-png", "-singlefile", pdf(name), page],
            check=True,
        )
        subprocess.run(["pdfimages", "-f", str(s.page), "-l", str(s.page), "-png", pdf(name), photo], check=True)
        cells += [page + ".png", f"{photo}-{s.image:03d}.png", shots[-1]["out"]]
    pictures.blender(doc, manifest, shots)
    w, h = CELL
    fit = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:white"
    graph = "".join(f"[{i}]{fit}[c{i}];" for i in range(len(cells)))
    layout = "|".join(f"{(i % 3) * w}_{(i // 3) * h}" for i in range(len(cells)))
    graph += "".join(f"[c{i}]" for i in range(len(cells))) + f"xstack=inputs={len(cells)}:layout={layout}:fill=white"
    ins = [a for c in cells for a in ("-i", c)]
    pictures.ffmpeg(*ins, "-filter_complex", graph, "-frames:v", "1", "-update", "1", os.path.join(OUT, name + ".png"))
    print(f"{name}: {len(steps)} steps -> {os.path.join(OUT, name + '.png')}")


if __name__ == "__main__":
    import sys

    for name in sys.argv[1:] or GUIDES:
        sheet(name)
