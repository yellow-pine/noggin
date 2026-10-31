"""The three Stages as data for the engine: every part (mesh file, neutral placement, material), the horns and their
four-bar chains, built from model/geometry.py exactly as the Fusion builders place them (model/eyes.py, pan_tilt.py,
mouth.py; the same align() frames and link() hole alignment). pose() gives every part's world transform at a horn angle.
Part names carry Fusion's ":1" occurrence suffix so reports line up with the recorded ones (model/reports)."""
import math, os
from collections import namedtuple

import numpy as np

from model import geometry as g
from model.engine import linkage

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REF = os.path.join(REPO, "docs", "references")
MODELS = {"eyes": os.path.join(REF, "01-eyes", "models"), "pt": os.path.join(REF, "02-pan-tilt", "models"),
          "mouth": os.path.join(REF, "03-mouth", "models")}
STEPS = os.path.join(REPO, "model", "build", "steps")   # model/engine/step_mesh.py output (make model-step-meshes)
SERVO_G = 16.0                      # docs/research/2026-10-31-electrical.md
STEP_G_CM3 = 1.9                    # boards, battery, horn: STEP volume x a PCB-like density (approximation, flagged in mass_source)
TOL_MM, TOL_INFERRED_MM = 0.5, 3.0  # placement tolerances, as check.py

Part = namedtuple("Part", "file matrix material clip")   # clip: (axis, max) local-frame cut, the battery lead
Loop = namedtuple("Loop", "joint solve coupler rockers rocker_pivot")   # rocker_pivot: (point, axis)
Horn = namedtuple("Horn", "pivot limits crank loops still")   # still: joints recorded as 0 (not in this chain)
Stage = namedtuple("Stage", "doc parts horns placements frame_up")
Pose = namedtuple("Pose", "parts joints")


def align(to_origin, to_x=None, to_z=None, from_origin=(0, 0, 0), from_x=(1, 0, 0), from_z=(0, 0, 1)):
    """4x4 taking the local frame (from_*) onto the world frame (to_*), mm; fusion_lib.align's frames."""
    def frame(origin, x, z):
        z = np.asarray(z, float); z = z / np.linalg.norm(z)
        x = np.asarray(x, float); x = x - (x @ z) * z; x = x / np.linalg.norm(x)
        m = np.eye(4); m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, np.cross(z, x), z, origin
        return m
    to_x = (1, 0, 0) if to_x is None else to_x
    to_z = (0, 0, 1) if to_z is None else to_z
    return frame(to_origin, to_x, to_z) @ np.linalg.inv(frame(from_origin, from_x, from_z))


def translate(p):
    return align(p)


def stl(stage, stem):
    return os.path.join(MODELS[stage], stem + ".stl")


def step(key):
    return os.path.join(STEPS, key + ".stl")


def printed(stem):
    """Material of a printed part from geometry.PRINTED (density g/cm3, source label)."""
    key = next(k for k in g.PRINTED if k.split(" (")[0] == stem)
    return g.MATERIALS[g.PRINTED[key][1]]["density_g_cm3"], g.PRINTED[key][1]


def part(file, matrix=None, material=None, clip=None):
    return Part(file, np.eye(4) if matrix is None else matrix, material, clip)


def link(stage, stl_key, hole_a, hole_b, normal):
    """The local-frame link STL with its holes on hole_a/hole_b (world mm), hole axis along normal (fusion_lib.link)."""
    spec = g.STL_LOCAL[stl_key]
    la, lb = spec["holes"]
    m = align(hole_a, np.subtract(hole_b, hole_a), normal, la, np.subtract(lb, la), spec["hole_axis"])
    return part(stl(stage, stl_key), m, printed(stl_key))


def servo_and_horn(key, label, arm):
    """(servo part, horn part) for SERVOS[key] with the horn's single arm along `arm` at neutral."""
    origin, tab_x, shaft = g.servo_frame(key)
    seat = np.add(origin, np.multiply(g.SERVO_STEP["horn_seat"], shaft))
    return {f"{label} servo:1": part(step("servo"), align(origin, tab_x, [-c for c in shaft], g.SERVO_STEP["shaft"]), (SERVO_G, "documented")),
            f"{label} horn (inferred):1": part(step("horn"), align(seat, arm, shaft, g.HORN_STEP["hub"]), (STEP_G_CM3, "step volume x 1.9 g/cm3"))}


def rocker_loop(joint, o2, a0, o4, b0, axis, coupler, rockers):
    return Loop(joint, linkage.four_bar(o2, a0, o4, b0, axis), coupler, rockers, (tuple(o4), tuple(axis)))


def limits(key):
    lo, hi = g.HORN_LIMITS[key]
    return lo - 90, hi - 90


def eyes_stage():
    parts, horns = {}, {}
    for name, stem, dx in [("L servo bracket", "L servo bracket", 0), ("R servo bracket", "R servo bracket", 0),
                           ("L eyeball", "L eyeball regular", 0), ("R eyeball", "R eyeball regular", 0),
                           ("L pupil", "regular pupil", -59), ("R pupil", "regular pupil", 0),
                           ("L inside lid", "inside lid", 0), ("L outside lid", "outside lid", 0),
                           ("R inside lid", "inside lid", 59), ("R outside lid", "outside lid", 59),
                           ("L eyeball bar", "eyeball bar", 0), ("R eyeball bar", "eyeball bar", 79)]:
        parts[name + ":1"] = part(stl("eyes", stem), translate((dx, 0, 0)), printed(stem))
    parts["main bracket v2:1"] = part(stl("mouth", "main bracket v2"), None, printed("main bracket v2"))
    parts["PandT base:1"] = part(stl("pt", "PandT base"), align(g.pt_to_eyes_standalone((0, 0, 0)), (-1, 0, 0), g.Y), printed("PandT base"))
    for s in "LR":
        side = (lambda p: p) if s == "L" else g.mirror_x
        lid_key, eye_key = f"{s.lower()}_lid", f"{s.lower()}_eye"
        parts.update(servo_and_horn(lid_key, f"{s} lid", g.Y))
        parts.update(servo_and_horn(eye_key, f"{s} eye", (-1, 0, 0) if s == "L" else g.X))
        lid_horn = g.PIVOTS[lid_key + "_horn"]["point"]
        normal = (-1, 0, 0) if s == "L" else (1, 0, 0)
        loops = []
        for key, stem in (("eyelid_bar", "eyelid bar"), ("eyelid_crank", "eyelid bar crank")):
            spec = g.LID_LINKS[key]
            x = side((spec["x"], 0, 0))[0]
            horn_pin = (x, lid_horn[1] + g.HORN_STEP["pin"], lid_horn[2])
            lid_pin = (x,) + side(g.LID_PINS[spec["lid"]])[1:]
            name = f"{s} {stem} (inferred):1"
            parts[name] = link("eyes", stem, horn_pin, lid_pin, normal)
            loops.append(rocker_loop(f"{s} {spec['lid']} lid pivot", lid_horn, horn_pin, g.PIVOTS[lid_key]["point"], lid_pin, g.X,
                                     name, [f"{s} {spec['lid']} lid:1"]))
        horns[f"{s} lid horn (inferred)"] = Horn(g.PIVOTS[lid_key + "_horn"], limits(lid_key), f"{s} lid horn (inferred):1", loops, [])
        arm_end, eye_end = (side(p) for p in g.EYEBALL_BAR_PINS)
        loop = rocker_loop(f"{s} eyeball pivot", g.PIVOTS[eye_key + "_horn"]["point"], arm_end, g.PIVOTS[eye_key]["point"], eye_end, g.Y,
                           f"{s} eyeball bar:1", [f"{s} eyeball:1", f"{s} pupil:1"])
        horns[f"{s} eye horn (inferred)"] = Horn(g.PIVOTS[eye_key + "_horn"], limits(eye_key), f"{s} eye horn (inferred):1", [loop], [])
    placements = [(f"{s} {p} servo:1", g.SERVO_STEP["tab_holes"], g.SERVOS[f"{s.lower()}_{p}"]["tab_holes"], TOL_INFERRED_MM) for s in "LR" for p in ("lid", "eye")]
    placements.append(("PandT base:1", [(0, 0, 0)], [g.pt_to_eyes_standalone((0, 0, 0))], TOL_MM))
    return Stage("noggin-eyes", parts, horns, placements, 1)


def electronics(n):
    """Receiver shield n with its Core flipped on top, switch board n and battery n on the PandT base (pan_tilt.py)."""
    stand = g.STANDOFFS["pt_base"]
    receiver_m = align(np.mean(stand[f"receiver_{n}"], axis=0), (0, -1, 0), (-1, 0, 0))
    flip = linkage.rotation(g.Z, 180, about=(0, 0.8, 0))
    pocket = g.BATTERY_POCKET_PT
    battery_at = (sum(pocket["x"]) / 2, pocket["y"][0], pocket["floor_z"] - g.BATTERY_STEP["floor_z"] + (n - 1) * 16.3)
    board = (STEP_G_CM3, "step volume x 1.9 g/cm3")
    return {f"receiver shield {n}:1": part(step("receiver"), receiver_m, board),
            f"Core {n} (flipped onto the shield top, per photo):1": part(step("core"), receiver_m @ flip, board),
            f"switch board {n} (inferred):1": part(step("switch"), align(stand["switch"][n - 1], (-1, 0, 0), g.Y, g.SWITCH_STEP["hole"]), board),
            ("battery 1:1" if n == 1 else "battery 2 (inferred):1"): part(step("battery"), align(battery_at, g.X, g.Z), board, ("y", g.BATTERY_STEP["lead_y"]))}


def pan_tilt_stage():
    parts = {}
    for name, stem, dz in [("PandT base", "PandT base", 0), ("bearing block", "PandT bearing block", 0), ("pan base", "PandT pan base", 0),
                           ("upright v2", "PandT upright v2", 0), ("tilt arm", "PandT tilt arm", g.TILT_ARM_SHIFT_Z),
                           ("servo mount plain", "PandT servo mount plain", 0), ("servo mount cutout", "PandT servo mount cutout", 0),
                           ("wire holder", "PandT wire holder", 0)]:
        parts[name + ":1"] = part(stl("pt", stem), translate((0, 0, dz)), printed(stem))
    bars = {}
    for key, stem in (("tilt", "tilt bar"), ("pan", "PandT bar")):
        pivot = g.PIVOTS[key + "_horn"]
        pin, lever = g.horn_pin(key)
        parts.update(servo_and_horn(key, key, np.subtract(pin, pivot["point"])))
        parts[f"{key} bar (inferred):1"] = link("pt", stem, pin, lever, pivot["axis"])
        bars[key] = pin, lever
    for n in (1, 2):
        parts.update(electronics(n))
    tilt = rocker_loop("tilt pivot", g.PIVOTS["tilt_horn"]["point"], bars["tilt"][0], g.PIVOTS["tilt"]["point"], bars["tilt"][1], g.X,
                       "tilt bar (inferred):1", ["tilt arm:1"])
    pan = rocker_loop("pan pivot", g.PIVOTS["pan_horn"]["point"], bars["pan"][0], g.PIVOTS["pan"]["point"], bars["pan"][1], g.Z,
                      "pan bar (inferred):1", ["pan base:1", "upright v2:1", "tilt servo:1", "tilt arm:1", "tilt horn (inferred):1", "tilt bar (inferred):1"])
    horns = {"tilt horn (inferred)": Horn(g.PIVOTS["tilt_horn"], limits("tilt"), "tilt horn (inferred):1", [tilt], ["pan pivot"]),
             "pan horn (inferred)": Horn(g.PIVOTS["pan_horn"], limits("rotate"), "pan horn (inferred):1", [pan], ["tilt pivot"])}
    stand = g.STANDOFFS["pt_base"]
    placements = [(f"{key} servo:1", g.SERVO_STEP["tab_holes"], g.SERVOS[key]["tab_holes"], TOL_INFERRED_MM) for key in ("tilt", "pan")]
    placements += [(f"receiver shield {n}:1", [(0, 0, 0)], [tuple(np.mean(stand[f"receiver_{n}"], axis=0))], TOL_MM) for n in (1, 2)]
    placements += [(f"switch board {n} (inferred):1", [g.SWITCH_STEP["hole"]], [stand["switch"][n - 1]], TOL_INFERRED_MM) for n in (1, 2)]
    return Stage("noggin-pan-tilt", parts, horns, placements, 2)


def mouth_stage():
    """The mouth parts plus the eyes Stage as grounded context (mouth.py inserts the saved noggin-eyes by reference)."""
    eyes = eyes_stage()
    parts = {}
    for name, stem in [("top jaw", "top jaw plain"), ("bottom jaw", "bottom jaw plain"), ("jaws servo mount", "jaws servo mount")]:
        parts[name + ":1"] = part(stl("mouth", stem), None, printed(stem))
    pin, lever = g.horn_pin("jaw")
    parts.update(servo_and_horn("jaw", "jaw", np.subtract(pin, g.PIVOTS["jaw_horn"]["point"])))
    parts["connector bar (inferred):1"] = link("mouth", "jaws connector bar", pin, lever, g.X)
    parts.update(eyes.parts)
    loop = rocker_loop("jaw hinge", g.PIVOTS["jaw_horn"]["point"], pin, g.PIVOTS["jaw_hinge"]["point"], lever, g.X, "connector bar (inferred):1", ["bottom jaw:1"])
    horns = {"jaw horn (inferred)": Horn(g.PIVOTS["jaw_horn"], limits("mouth"), "jaw horn (inferred):1", [loop], [])}
    placements = [("jaw servo:1", g.SERVO_STEP["tab_holes"], g.SERVOS["jaw"]["tab_holes"], TOL_INFERRED_MM)]
    return Stage("noggin-mouth", parts, horns, placements, 1)


STAGES = {s.doc: s for s in (eyes_stage(), pan_tilt_stage(), mouth_stage())}
CONTEXT = {"noggin-mouth": "noggin-eyes"}   # Stage inserted whole as grounded context: reported as one part, measured as its parts


def world(m, p):
    return tuple((m @ np.array([*p, 1.0]))[:3])


def placements(stage):
    """check.placements for the engine: parts whose placed points miss the geometry tables. Pivots are at PIVOTS by
    construction here, so only the parts can disagree."""
    out = []
    for name, local_pts, expected, tol in stage.placements:
        actual = [world(stage.parts[name].matrix, q) for q in local_pts]
        worst = max(min(math.dist(a, e) for a in actual) for e in expected)
        if worst > tol:
            out.append({"placement": name, "mm": round(worst, 2), "tol": tol, "actual": [[round(c, 2) for c in a] for a in actual]})
    return out


def pose(stage, horn_name, deg):
    """Every part's world 4x4 with the horn at `deg` (degrees from neutral about its pivot axis) and the driven
    joint angles. Raises linkage.Unreachable when a loop cannot close."""
    horn = stage.horns[horn_name]
    mats = {name: p.matrix for name, p in stage.parts.items()}
    crank = linkage.rotation(horn.pivot["axis"], deg, horn.pivot["point"])
    mats[horn.crank] = crank @ mats[horn.crank]
    joints = {j: 0.0 for j in horn.still}
    for loop in horn.loops:
        rocker, a, b = loop.solve(deg)
        _, a0, b0 = loop.solve(0)
        axis = loop.rocker_pivot[1]
        twist = _angle(axis, np.subtract(b, a)) - _angle(axis, np.subtract(b0, a0))
        mats[loop.coupler] = linkage.rotation(axis, math.degrees(twist), a) @ translate(np.subtract(a, a0)) @ mats[loop.coupler]
        turn = linkage.rotation(axis, rocker, loop.rocker_pivot[0])
        for name in loop.rockers:
            mats[name] = turn @ mats[name]
        joints[loop.joint] = round(rocker, 2)
    return Pose(mats, joints)


def _angle(axis, v):
    u, w = linkage._PLANE[tuple(axis)]
    return math.atan2(v[w], v[u])
