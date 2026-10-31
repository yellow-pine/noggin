"""The Mech as data for the engine: the four sub-assemblies (base, stack, eyes, mouth: every part with its mesh file,
neutral placement and material, the horns and their four-bar chains) built from model/geometry.py exactly as the Fusion
builders place them (model/base.py, stack.py, eyes.py, mouth.py: the same align() frames and link() hole alignment), and
assemble() putting sub-assemblies at frames into one document: the recorded sweep documents (model/reports) and the Stage
configurations of geometry.STAGES. pose() gives every part's world transform at a horn angle. Part names carry Fusion's
":1" occurrence suffix so reports line up with the recorded ones."""

import math
import os
from collections import namedtuple

import numpy as np

from model import geometry as g
from model.engine import linkage

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REF = os.path.join(REPO, "docs", "references")
MODELS = {
    "eyes": os.path.join(REF, "01-eyes", "models"),
    "pt": os.path.join(REF, "02-pan-tilt", "models"),
    "mouth": os.path.join(REF, "03-mouth", "models"),
}
STEPS = os.path.join(REPO, "model", "build", "steps")  # model/engine/step_mesh.py output (make model-step-meshes)
SERVO_G = 16.0  # docs/research/2026-10-31-electrical.md
STEP_G_CM3 = 1.9  # boards, battery, horn: STEP volume x a PCB-like density (approximation, flagged in mass_source)
TOL_MM, TOL_INFERRED_MM = 0.5, 3.0  # placement tolerances: measured, inferred (+-4 mm pivots, +-3 mm bar planes)

Part = namedtuple("Part", "file matrix material clip")  # clip: (axis, max) local-frame cut, the battery and servo leads
Loop = namedtuple("Loop", "joint solve coupler rockers rocker_pivot")  # rocker_pivot: (point, axis)
Horn = namedtuple(
    "Horn", "pivot limits crank loops still frame"
)  # still: joints recorded as 0 (not in this chain); frame: the sub-assembly's 4x4
Sub = namedtuple(
    "Sub", "parts horns placements ports"
)  # ports: {Port name: (part, local mm)}, as the Fusion builds name them
Doc = namedtuple(
    "Doc", "doc parts horns placements up ports"
)  # up: index of the document frame's up axis (gravity torque)
Pose = namedtuple("Pose", "parts joints")


def align(*frames, **kw):
    """4x4 taking the local frame onto the world frame, mm (geometry.align_rows, the Fusion builds' frames)."""
    return np.array(g.align_rows(*frames, **kw))


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


def link_placement(name, stl_key, hole_a, hole_b, pin_axis=None, tol=None):
    """The link's two holes on its pins, in the plane of the loop: along the pin axis a link may sit anywhere on its pin
    (the crank's lid end is stepped 3 mm). pin_axis (0, 1 or 2) is the world pin direction when the two pins sit at
    different depths along it (the eyelid crank): the expected lid-end point then takes the horn end's depth too."""
    spec = g.STL_LOCAL[stl_key]
    la, lb = spec["holes"]
    i = spec["hole_axis"].index(1)
    lb = tuple(la[i] if k == i else c for k, c in enumerate(lb))
    if pin_axis is not None:
        hole_b = tuple(hole_a[pin_axis] if k == pin_axis else c for k, c in enumerate(hole_b))
    return (name, [la, lb], [hole_a, hole_b], tol or (TOL_INFERRED_MM if "(inferred)" in name else TOL_MM))


def servo_placements(key, label):
    """The servo's tab holes on its pair and its horn's hub (spline-side face) on the horn pivot."""
    hub = (*g.HORN_STEP["hub"][:2], g.HORN_STEP["height"])
    return [
        (f"{label} servo:1", g.SERVO_STEP["tab_holes"], g.SERVOS[key]["tab_holes"], TOL_MM),
        (f"{label} horn:1", [hub], [g.PIVOTS[key + "_horn"]["point"]], TOL_MM),
    ]


def servo_port(label):
    """Where the servo's lead leaves it (its cable exit): the Port its cable corridor starts from (model/engine/cables.py)."""
    return {f"{label} servo lead": (f"{label} servo:1", g.SERVO_STEP["lead"])}


def servo_and_horn(key, label, arm):
    """(servo part, horn part) for SERVOS[key] with the horn's single arm along `arm` at neutral."""
    origin, tab_x, shaft = g.servo_frame(key)
    seat = np.add(origin, np.multiply(g.SERVO_STEP["horn_seat"], shaft))
    return {
        f"{label} servo:1": part(
            step("servo"),
            align(origin, tab_x, [-c for c in shaft], g.SERVO_STEP["shaft"]),
            (SERVO_G, "documented"),
            ("x", g.SERVO_STEP["lead"][0]),
        ),
        f"{label} horn:1": part(
            # spline side (local z 4.15) on the seat, the arm on the outer face (docs/research/2026-10-31-shafts.md)
            step("horn"),
            align(
                np.add(seat, np.multiply(g.HORN_STEP["height"], shaft)), arm, [-c for c in shaft], g.HORN_STEP["hub"]
            ),
            (STEP_G_CM3, "step volume x 1.9 g/cm3"),
        ),
    }


def rocker_loop(joint, o2, a0, o4, b0, axis, coupler, rockers):
    return Loop(joint, linkage.four_bar(o2, a0, o4, b0, axis), coupler, rockers, (tuple(o4), tuple(axis)))


def limits(key):
    lo, hi = g.HORN_LIMITS[key]
    return lo - 90, hi - 90


def eyes():
    parts, horns = {}, {}
    for name, stem, dx in g.EYES_PARTS:
        parts[name + ":1"] = part(stl("eyes", stem), translate((dx, 0, 0)), printed(stem))
    parts["main bracket v2:1"] = part(stl("mouth", "main bracket v2"), None, printed("main bracket v2"))
    placements = []
    for s in "LR":
        side = (lambda p: p) if s == "L" else g.mirror_x
        lid_key, eye_key = f"{s.lower()}_lid", f"{s.lower()}_eye"
        parts.update(servo_and_horn(lid_key, f"{s} lid", g.LID_HORN_ARM))
        parts.update(servo_and_horn(eye_key, f"{s} eye", (-1, 0, 0) if s == "L" else g.X))
        lid_horn = g.PIVOTS[lid_key + "_horn"]["point"]
        normal = (1, 0, 0) if s == "L" else (-1, 0, 0)  # inboard: the crank's step toward the lid ear
        loops = []
        for key, stem in (("eyelid_bar", "eyelid bar"), ("eyelid_crank", "eyelid bar crank")):
            spec = g.LID_LINKS[key]
            hx, lx = (side((x, 0, 0))[0] for x in spec["x"])
            horn_pin = (hx, *(c + g.HORN_STEP["pin"] * a for c, a in zip(lid_horn[1:], g.LID_HORN_ARM[1:])))
            lid_pin = (lx,) + side(g.LID_PINS[spec["lid"]])[1:]
            name = f"{s} {stem}:1"
            parts[name] = link("eyes", stem, horn_pin, lid_pin, normal)
            # lid pins run along X; the horn pin is 41.14 / 40.86 from them for 41 mm bars (geometry.LID_HORN_ARM)
            placements.append(link_placement(name, stem, horn_pin, lid_pin, pin_axis=0))
            loops.append(
                rocker_loop(
                    f"{s} {spec['lid']} lid pivot",
                    lid_horn,
                    horn_pin,
                    g.PIVOTS[lid_key]["point"],
                    lid_pin,
                    g.X,
                    name,
                    [f"{s} {spec['lid']} lid:1"],
                )
            )
        horns[f"{s} lid horn"] = Horn(g.PIVOTS[lid_key + "_horn"], limits(lid_key), f"{s} lid horn:1", loops, [], None)
        arm_end, eye_end = (side(p) for p in g.EYEBALL_BAR_PINS)
        loop = rocker_loop(
            f"{s} eyeball pivot",
            g.PIVOTS[eye_key + "_horn"]["point"],
            arm_end,
            g.PIVOTS[eye_key]["point"],
            eye_end,
            g.Y,
            f"{s} eyeball bar:1",
            [f"{s} eyeball:1", f"{s} pupil:1"],
        )
        horns[f"{s} eye horn"] = Horn(g.PIVOTS[eye_key + "_horn"], limits(eye_key), f"{s} eye horn:1", [loop], [], None)
    placements += [pl for s in "LR" for p in ("lid", "eye") for pl in servo_placements(f"{s.lower()}_{p}", f"{s} {p}")]
    ports = {n: p for s in "LR" for k in ("lid", "eye") for n, p in servo_port(f"{s} {k}").items()}
    return Sub(parts, horns, placements, ports)


def electronics(n):
    """(parts, ports): receiver shield n with its Core flipped on top, switch board n and battery n on the PandT base
    (model/electronics.py)."""
    receiver_m = align(g.receiver_at(n), *g.RECEIVER_AXES)
    axis, deg, about = g.CORE_FLIP
    flip = linkage.rotation(axis, deg, about)
    board = (STEP_G_CM3, "step volume x 1.9 g/cm3")
    shield, switch = f"receiver shield {n}:1", f"switch board {n}" + (" (inferred)" if n == 2 else "") + ":1"
    battery = "battery 1:1" if n == 1 else "battery 2 (inferred):1"
    ports = {f"Core {n} servo {h}": (shield, p) for h, p in g.RECEIVER_STEP["headers"].items()}
    ports[f"Core {n} XH power"] = (shield, g.RECEIVER_STEP["xh_power"])
    ports[f"battery {n} lead"] = (battery, g.BATTERY_STEP["plug"])
    ports[f"switch board {n} hole"] = (switch, g.SWITCH_STEP["hole"])  # its XH sockets are not located [I]
    return {
        shield: part(step("receiver"), receiver_m, board),
        f"Core {n} (flipped onto the shield top, per photo):1": part(step("core"), receiver_m @ flip, board),
        switch: part(step("switch"), align(*g.switch_at(n), g.SWITCH_STEP["hole"]), board),
        battery: part(step("battery"), align(g.battery_at(n), g.X, g.Z), board, ("y", g.BATTERY_STEP["lead_y"])),
    }, ports


def base():
    """noggin-base: the PandT base plate with electronics set 1, PT frame (model/base.py)."""
    set1, ports = electronics(1)
    parts = {"PandT base:1": part(stl("pt", "PandT base"), None, printed("PandT base")), **set1}
    stand = g.STANDOFFS["pt_base"]
    placements = [
        ("receiver shield 1:1", [(0, 0, 0)], [tuple(np.mean(stand["receiver_1"], axis=0))], TOL_MM),
        ("switch board 1:1", [g.SWITCH_STEP["hole"]], [stand["switch_post"][0]], TOL_MM),
    ]
    return Sub(parts, {}, placements, ports)


def stack():
    """noggin-stack: the pan-tilt neck with electronics set 2, PT frame (model/stack.py)."""
    parts = {}
    for name, stem, shift in g.STACK_PARTS:
        parts[name + ":1"] = part(stl("pt", stem), translate(shift), printed(stem))
    bars, placements = {}, []
    for key, stem in (("tilt", "tilt bar"), ("pan", "PandT bar")):
        pivot = g.PIVOTS[key + "_horn"]
        pin, lever = g.horn_pin(key)
        parts.update(servo_and_horn(key, key, np.subtract(pin, pivot["point"])))
        parts[f"{key} bar:1"] = link("pt", stem, pin, lever, pivot["axis"])
        bars[key] = pin, lever
        placements += [*servo_placements(key, key), link_placement(f"{key} bar:1", stem, pin, lever)]
    set2, ports = electronics(2)
    parts.update(set2)
    ports.update({**servo_port("tilt"), **servo_port("pan")})
    tilt = rocker_loop(
        "tilt pivot",
        g.PIVOTS["tilt_horn"]["point"],
        bars["tilt"][0],
        g.PIVOTS["tilt"]["point"],
        bars["tilt"][1],
        g.X,
        "tilt bar:1",
        ["tilt arm:1"],
    )
    pan = rocker_loop(
        "pan pivot",
        g.PIVOTS["pan_horn"]["point"],
        bars["pan"][0],
        g.PIVOTS["pan"]["point"],
        bars["pan"][1],
        g.Z,
        "pan bar:1",
        ["pan base:1", "upright v2:1", "tilt servo:1", "tilt arm:1", "tilt horn:1", "tilt bar:1"],
    )
    horns = {
        "tilt horn": Horn(g.PIVOTS["tilt_horn"], limits("tilt"), "tilt horn:1", [tilt], ["pan pivot"], None),
        "pan horn": Horn(g.PIVOTS["pan_horn"], limits("rotate"), "pan horn:1", [pan], ["tilt pivot"], None),
    }
    stand = g.STANDOFFS["pt_base"]
    placements += [
        ("receiver shield 2:1", [(0, 0, 0)], [tuple(np.mean(stand["receiver_2"], axis=0))], TOL_MM),
        ("switch board 2 (inferred):1", [g.SWITCH_STEP["hole"]], [stand["switch"][1]], TOL_INFERRED_MM),
    ]
    return Sub(parts, horns, placements, ports)


def mouth():
    """noggin-mouth's own parts, eyes frame (model/mouth.py; its context copy of the eyes is assembled separately)."""
    parts = {}
    for name, stem in g.MOUTH_PARTS:
        parts[name + ":1"] = part(stl("mouth", stem), None, printed(stem))
    pin, lever = g.horn_pin("jaw")
    parts.update(servo_and_horn("jaw", "jaw", np.subtract(pin, g.PIVOTS["jaw_horn"]["point"])))
    parts["connector bar:1"] = link("mouth", "jaws connector bar", pin, lever, g.X)
    loop = rocker_loop(
        "jaw hinge",
        g.PIVOTS["jaw_horn"]["point"],
        pin,
        g.PIVOTS["jaw_hinge"]["point"],
        lever,
        g.X,
        "connector bar:1",
        ["bottom jaw:1"],
    )
    horns = {"jaw horn": Horn(g.PIVOTS["jaw_horn"], limits("mouth"), "jaw horn:1", [loop], [], None)}
    placements = [
        *servo_placements("jaw", "jaw"),
        link_placement("connector bar:1", "jaws connector bar", pin, lever, pin_axis=0),  # cranked 13 mm along X
    ]
    return Sub(parts, horns, placements, servo_port("jaw"))


SUBS = {"noggin-base": base, "noggin-stack": stack, "noggin-eyes": eyes, "noggin-mouth": mouth}
EYES_FRAME = (0, 0, 0), g.X, g.Z
BASE_IN_EYES = (
    g.pt_to_eyes_standalone((0, 0, 0)),
    (-1, 0, 0),
    g.Y,
)  # the base as the eyes/mouth sweep documents carried it (context)
# Documents the engine simulates: the recorded sweep documents (the gate fixtures in model/reports, in their own frames,
# with the sub-assemblies they carried as grounded context: no horns swept, as Fusion sweeps root joints only) and the
# Stage configurations (geometry.STAGES, PT frame, every horn). Frames are (origin, x axis, z axis) as fusion_lib.align.
DOCS = {
    "noggin-eyes": ({"noggin-eyes": EYES_FRAME, "noggin-base": BASE_IN_EYES}, 1, {"noggin-base"}),
    "noggin-pan-tilt": ({"noggin-base": ((0, 0, 0), g.X, g.Z), "noggin-stack": ((0, 0, 0), g.X, g.Z)}, 2, set()),
    "noggin-mouth": (
        {"noggin-mouth": EYES_FRAME, "noggin-eyes": EYES_FRAME, "noggin-base": BASE_IN_EYES},
        1,
        {"noggin-eyes", "noggin-base"},
    ),
    **{doc: (frames, 2, set()) for doc, frames in g.STAGES.items()},
}


RIDES = {
    "noggin-eyes": lambda doc: g.STEM_IN[doc] + ":1",
    "noggin-mouth": lambda doc: "main bracket v2:1",
}  # clamped to that part


def assemble(doc, frames, up, context=()):
    """One document: each sub-assembly's parts and horns carried to its frame (parts static there unless a horn moves
    them); `context` sub-assemblies bring parts only. In a Stage configuration the eyes are clamped to STEM_IN's part
    and the mouth to the bracket (model/stage.py's as-built joints), so they ride every chain that part rocks on.
    Part names are unique across the sub-assemblies by construction."""
    parts, horns, placements, owner, ports = {}, {}, [], {}, {}
    for name, frame in frames.items():
        sub, f = SUBS[name](), align(*frame)
        for pname, p in sub.parts.items():
            assert pname not in parts, pname
            parts[pname] = Part(p.file, f @ p.matrix, p.material, p.clip)
            owner[pname] = name
        if name not in context:
            horns.update({h: horn._replace(frame=f) for h, horn in sub.horns.items()})
        placements += [
            (pname, local, [world(f, e) for e in expected], tol) for pname, local, expected, tol in sub.placements
        ]
        ports.update(sub.ports)  # part-local: they ride their part
    if doc in g.STEM_AT:  # the bracket stem in STEM_IN's part
        placements.append(("main bracket v2:1", [g.STEM_BOTTOM], [g.STEM_AT[doc]], TOL_INFERRED_MM))
    if doc in g.STEM_IN:
        riders = {}  # carrier part -> parts clamped to it (the mouth on the bracket, the bracket on the tilt arm)
        for sub, carrier in RIDES.items():
            if sub in frames:
                riders.setdefault(carrier(doc), []).extend(n for n in parts if owner[n] == sub)
        for h, horn in horns.items():
            loops = []
            for loop in horn.loops:
                rockers = list(loop.rockers)
                todo = list(rockers)
                while todo:  # transitive: a carried part may carry more
                    for n in riders.get(todo.pop(), []):
                        if n not in rockers:
                            rockers.append(n)
                            todo.append(n)
                loops.append(loop._replace(rockers=rockers))
            horns[h] = horn._replace(loops=loops)
    return Doc(doc, parts, horns, placements, up, ports)


def stage(doc):
    frames, up, context = DOCS[doc]
    return assemble(doc, frames, up, context)


class _Stages(dict):
    def __missing__(self, doc):
        self[doc] = stage(doc)
        return self[doc]


STAGES = _Stages()  # built on first use: a document per DOCS key


def world(m, p):
    return tuple((m @ np.array([*p, 1.0]))[:3])


def placements(stage):
    """Parts whose placed points miss the geometry tables by more than their tolerance. Pivots are at PIVOTS by
    construction here, so only the parts can disagree."""
    out = []
    for name, local_pts, expected, tol in stage.placements:
        actual = [world(stage.parts[name].matrix, q) for q in local_pts]
        worst = max(min(math.dist(a, e) for a in actual) for e in expected)
        if worst > tol:
            out.append(
                {
                    "placement": name,
                    "mm": round(worst, 2),
                    "tol": tol,
                    "actual": [[round(c, 2) for c in a] for a in actual],
                }
            )
    return out


def pose(stage, horn_name, deg):
    """Every part's world 4x4 with the horn at `deg` (degrees from neutral about its pivot axis) and the driven
    joint angles. Raises linkage.Unreachable when a loop cannot close."""
    horn = stage.horns[horn_name]
    mats = {name: p.matrix for name, p in stage.parts.items()}
    f, f_inv = horn.frame, np.linalg.inv(horn.frame)  # the chain solves in its sub-assembly's frame

    def move(name, delta):
        mats[name] = f @ delta @ f_inv @ mats[name]

    move(horn.crank, linkage.rotation(horn.pivot["axis"], deg, horn.pivot["point"]))
    joints = {j: 0.0 for j in horn.still}
    for loop in horn.loops:
        rocker, a, b = loop.solve(deg)
        _, a0, b0 = loop.solve(0)
        axis = loop.rocker_pivot[1]
        twist = _angle(axis, np.subtract(b, a)) - _angle(axis, np.subtract(b0, a0))
        move(loop.coupler, linkage.rotation(axis, math.degrees(twist), a) @ translate(np.subtract(a, a0)))
        turn = linkage.rotation(axis, rocker, loop.rocker_pivot[0])
        for name in loop.rockers:
            move(name, turn)
        joints[loop.joint] = round(rocker, 2)
    return Pose(mats, joints)


def _angle(axis, v):
    u, w = linkage._PLANE[tuple(axis)]
    return math.atan2(v[w], v[u])
