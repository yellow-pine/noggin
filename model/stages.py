"""The next Mech as data: its sub-assemblies (every part with its mesh file, neutral placement and material, the horns
and their four-bar chains) built from model/gimbal.py, model/neck.py and model/base.py, and assemble() putting
sub-assemblies at frames into one document (geometry.NEXT). pose() gives every part's world transform at a horn angle by
the four-bar kinematics (model/linkage.py), exactly, without simulating. Part names carry a ":1" suffix, as MuJoCo's
bodies and the GLBs' nodes."""

import math
import os
from collections import namedtuple

import numpy as np

from model import base as candidates
from model import geometry as g
from model import gimbal, linkage, neck

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OURS = os.path.join(
    REPO, "model", "build", "ours"
)  # our printed parts and hardware envelopes (model/ours.py, just ours)
SERVO_G = 16.0  # docs/research/2026-10-31-electrical.md
STEP_G_CM3 = 1.9  # boards, battery, horn: STEP volume x a PCB-like density (approximation, flagged in mass_source)
BOARD = (STEP_G_CM3, "step volume x 1.9 g/cm3")

Part = namedtuple("Part", "file matrix material clip")  # clip: (axis, max) local-frame cut, the battery and servo leads
Loop = namedtuple("Loop", "joint solve coupler rockers rocker_pivot")  # rocker_pivot: (point, axis)
Horn = namedtuple(
    "Horn", "pivot limits crank loops still frame rods", defaults=((),)
)  # still: joints recorded as 0 (not in this chain); frame: the sub-assembly's 4x4; rods: its Rods
# A rod riding another moving part, the `carrier` (the next Mech's pitch push-rods on the bail, #663; each lower lid's
# link on its lid bar, #698): `part` on a `joint` at `arm` (about `axes`: two, a universal joint), its other end on
# `lever`, the lever of the parts `driven` turn on their own `hinge` (joint, point, axis): a loop closed at `lever` as a
# four-bar is at its rocker pin.
Rod = namedtuple("Rod", "joint part carrier arm axes hinge driven lever")
Sub = namedtuple("Sub", "parts horns")
Doc = namedtuple("Doc", "doc parts horns")
Pose = namedtuple("Pose", "parts joints")


def align(*frames, **kw):
    """4x4 taking the local frame onto the world frame, mm (geometry.align_rows)."""
    return np.array(g.align_rows(*frames, **kw))


def translate(p):
    return align(p)


def stl(stem):
    """Our part's mesh (just ours): a printed part or a hardware envelope."""
    return os.path.join(OURS, stem + ".stl")


def stem(file):
    """The part a mesh file holds (stl's inverse)."""
    return os.path.splitext(os.path.basename(file))[0]


def printed(stem):
    """Material of a printed part from geometry.PRINTED (density g/cm3, source label)."""
    key = next(k for k in g.PRINTED if k.split(" (")[0] == stem)
    return g.MATERIALS[g.PRINTED[key][1]]["density_g_cm3"], g.PRINTED[key][1]


def part(file, matrix=None, material=None, clip=None):
    return Part(file, np.eye(4) if matrix is None else matrix, material, clip)


def mounted(origin, tab_x, shaft, label, arm):
    """(servo part, horn part): the servo's tab mid-plane under its shaft at `origin`, tabs along tab_x, the horn's arm
    along `arm`."""
    seat = np.add(origin, np.multiply(g.SERVO_STEP["horn_seat"], shaft))
    return {
        f"{label} servo:1": part(
            stl("servo"),
            align(origin, tab_x, [-c for c in shaft], g.SERVO_STEP["shaft"]),
            (SERVO_G, "documented"),
            ("x", g.SERVO_STEP["lead"][0]),
        ),
        f"{label} horn:1": part(
            # spline side (local z 4.15) on the seat, the arm on the outer face (docs/research/2026-10-31-shafts.md)
            stl("horn"),
            align(
                np.add(seat, np.multiply(g.HORN_STEP["height"], shaft)), arm, [-c for c in shaft], g.HORN_STEP["hub"]
            ),
            (STEP_G_CM3, "step volume x 1.9 g/cm3"),
        ),
    }


def rocker_loop(joint, o2, a0, o4, b0, axis, coupler, rockers):
    return Loop(joint, linkage.four_bar(o2, a0, o4, b0, axis), coupler, rockers, (tuple(o4), tuple(axis)))


def next_base():
    """next-base: the next Mech's Torso (#685, model/base.py) with the pack lying across x on its floor, its lead out to
    -x, the same in every head variant."""
    pack = align((candidates.PACK[0] / 2, candidates.PACK_Y, neck.MOUNT_Z[0] - g.BATTERY_STEP["floor_z"]), g.Y)
    parts = {
        "next torso:1": part(stl("next torso"), None, printed("next torso")),
        "next pack:1": part(stl("battery"), pack, BOARD, ("y", g.BATTERY_STEP["lead_y"])),
    }
    return Sub(parts, {})


def _boards(stem, placed):
    """The carrier's part and the boards on it, placed (model/base.py)."""
    parts = {f"{stem}:1": part(stl(stem), None, printed(stem))}
    parts |= {f"{name}:1": part(stl(mesh), at, BOARD) for name, (mesh, at) in placed.items()}
    return Sub(parts, {})


def next_back():
    """next-back: the boards upright on the board rack's back face, behind the eye gimbal; it rides the head (RIDES)."""
    return _boards("next board rack", candidates.back_boards())


def next_eyes():
    """next-eyes: the next Mech's eye gimbal (#630, model/gimbal.py) at rest, in its own frame: per eye the core, its
    cap, yoke, push-rod, upper and lower lid, lid bar and link; the tie-bar, the bail, the pitch bar and the frame; the
    eyes Core's servos with their horns on the drives, each a hinge MuJoCo drives (#663): the upper lids and the pitch
    horn's bail through their four-bars, both yokes off the yaw horn's tie-bar, each core pitched on its yoke by its
    push-rod off the bail and each lower lid by its link off the lid bar (Rods, #698). Kinematics and its report:
    model/gimbal.py."""
    parts, horns = {}, {}
    for s, (cx, _, _) in gimbal.EYE.items():
        at = translate(gimbal.EYE[s])
        sign = 1 if s == "L" else -1
        for name, stem, m in (
            ("eyeball core", "next eyeball core", at),
            ("eyeball cap", f"next {s} eyeball cap", at),
            ("yaw yoke", "next yaw yoke", at),
            ("push-rod", "next push-rod", translate((cx, 0, 0))),
            ("upper lid", f"next {s} upper lid", at),
            ("lower lid", f"next {s} lower lid", at),
            ("lid bar", "next lid bar", translate((cx - sign * sum(gimbal.LID_X["bar"]) / 2, 0, 0))),
            ("lid link", "next lid link", translate((cx - sign * sum(gimbal.LID_X["link"]) / 2, 0, 0))),
        ):
            parts[f"next {s} {name}:1"] = part(stl(stem), m, printed(stem))
    for stem in ("next tie-bar", "next bail", "next pitch bar", "next gimbal frame"):
        parts[stem + ":1"] = part(stl(stem), None, printed(stem))
    for label, (face, shaft, tab, arm) in gimbal.drives().items():
        parts.update(mounted(gimbal.servo_origin(face, shaft), tab, shaft, f"next {label}", arm))
    lo, hi = (gimbal.servos(0, p)[1] for p in (gimbal.PITCH, -gimbal.PITCH))
    limits = {
        "yaw": (-gimbal.YAW, gimbal.YAW),
        "pitch": (lo, hi),
        "lid": tuple(e - gimbal.LID_REST for e in gimbal.LID_EDGES),
    }
    crank = gimbal.CRANK
    yaw = (0.0, gimbal.YAW_Y, gimbal.TIE_Z[1])  # the tie-bar's plane, under the yokes' cranks
    horns["next yaw horn"] = Horn(
        {"point": yaw, "axis": g.Z},
        limits["yaw"],
        "next yaw horn:1",
        [
            rocker_loop(
                f"next {s} yaw pivot",
                yaw,
                (0.0, gimbal.YAW_Y + crank, yaw[2]),
                (x, 0.0, yaw[2]),
                (x, crank, yaw[2]),
                g.Z,
                "next tie-bar:1",
                [f"next {s} {p}:1" for p in ("yaw yoke", "eyeball core", "eyeball cap")],
            )
            for s, (x, _, _) in gimbal.EYE.items()
        ],
        [],
        None,
    )
    horn, bail = (0.0, *gimbal.PITCH_HORN), (0.0, *gimbal.BAIL)
    horns["next pitch horn"] = Horn(
        {"point": horn, "axis": g.X},
        limits["pitch"],
        "next pitch horn:1",
        [
            rocker_loop(
                "next bail pivot",
                horn,
                (0.0, horn[1] + crank, horn[2]),
                bail,
                (0.0, bail[1] + gimbal.BAIL_IN, bail[2]),
                g.X,
                "next pitch bar:1",
                ["next bail:1"],
            )
        ],
        [],
        None,
        [
            Rod(
                f"next {s} push-rod",
                f"next {s} push-rod:1",
                "next bail:1",
                (x, bail[1], bail[2] + gimbal.LEVER),
                (g.X, g.Z),
                (f"next {s} eyeball pitch", (x, 0.0, 0.0), (-1, 0, 0)),  # pitch up positive, as gimbal.core
                [f"next {s} eyeball core:1", f"next {s} eyeball cap:1"],
                (x, 0.0, gimbal.LEVER),
            )
            for s, (x, _, _) in gimbal.EYE.items()
        ],
    )
    for s, (x, _, _) in gimbal.EYE.items():  # lid servo positive opens: about -x, as gimbal.moved
        horn = (x, *gimbal.LID_HORN)
        horns[f"next {s} lid horn"] = Horn(
            {"point": horn, "axis": (-1, 0, 0)},
            limits["lid"],
            f"next {s} lid horn:1",
            [
                rocker_loop(
                    f"next {s} lid pivot",
                    horn,
                    (x, *np.add(gimbal.LID_HORN, gimbal.LID_PIN)),
                    (x, 0.0, 0.0),
                    (x, *gimbal.LID_PIN),
                    (-1, 0, 0),
                    f"next {s} lid bar:1",
                    [f"next {s} upper lid:1"],
                )
            ],
            [],
            None,
            [
                Rod(
                    f"next {s} lid link",
                    f"next {s} lid link:1",
                    f"next {s} lid bar:1",
                    (x, *gimbal.LINK_PIN),
                    (-1, 0, 0),
                    (f"next {s} lower lid pivot", (x, 0.0, 0.0), (-1, 0, 0)),  # up positive, as gimbal.lower
                    [f"next {s} lower lid:1"],
                    (x, *gimbal.LOWER_PIN),
                )
            ],
        )
    return Sub(parts, horns)


def next_neck():
    """next-neck: the next Mech's neck and jaw (#641, model/neck.py) at rest, in the head's frame (the gimbal's): the
    neck mount, the pan yoke, the head mount, the jaw and their bars, the neck Core's servos with their horns on the
    drives. Each drive turns its horn as today's Stages do, so the MuJoCo report and the Core's servo names apply (#642):
    the pan carries the yoke and the head, the tilt the head (neck.HEAD, and what rides the head mount: RIDES), the
    mouth the jaw."""
    parts = {
        f"{stem}:1": part(stl(stem), None, printed(stem))
        for stem in (
            "next neck mount",
            "next pan yoke",
            "next head mount",
            "next jaw",
            "next pan bar",
            "next tilt bar",
            "next jaw bar",
        )
    }
    for label, (face, shaft, tab, arm) in neck.drives().items():
        parts.update(mounted(gimbal.servo_origin(face, shaft), tab, shaft, f"next {label}", arm))
    pins, head = neck.pins(), list(neck.HEAD)
    carried = {
        "pan": ["next pan yoke:1", "next tilt servo:1", "next tilt horn:1", "next tilt bar:1", *head],
        "tilt": head,
        "jaw": ["next jaw:1"],
    }
    horns = {}
    for drive, crank, horn, bar in (
        ("pan", "next pan horn:1", "pan horn", "next pan bar:1"),
        ("tilt", "next tilt horn:1", "tilt horn", "next tilt bar:1"),
        ("jaw", "next mouth horn:1", "jaw horn", "next jaw bar:1"),
    ):
        o4, _, o2, axis = pins[drive]
        loop = Loop(f"{drive} pivot", neck.LINKAGES[drive], bar, carried[drive], (tuple(o4), tuple(axis)))
        ends = sorted(neck.servo_for(drive, d) if d else 0.0 for d in neck.RANGES[drive])
        still = [f"{d} pivot" for d in neck.RANGES if d != drive]
        horns[horn] = Horn({"point": o2, "axis": axis}, tuple(ends), crank, [loop], still, None)
    return Sub(parts, horns)


SUBS = {
    "next-eyes": next_eyes,
    "next-neck": next_neck,
    "next-base": next_base,
    "next-back": next_back,
}
# The documents the model simulates: {document: {sub-assembly: its frame}}, each frame (origin, x axis, z axis) as
# geometry.align_rows
DOCS = g.NEXT
RIDES = {
    "next-eyes": "next head mount:1",  # the gimbal frame screwed on its flange
    "next-back": "next head mount:1",  # the rack under the plate
}  # clamped to that part


def assemble(doc, frames):
    """One document: each sub-assembly's parts and horns carried to its frame (parts static there unless a horn moves
    them), what RIDES a part clamped to it, so it rides every chain that part rocks on. Part names are unique across the
    sub-assemblies by construction."""
    parts, horns, owner = {}, {}, {}
    for name, frame in frames.items():
        sub, f = SUBS[name](), align(*frame)
        for pname, p in sub.parts.items():
            assert pname not in parts, pname
            parts[pname] = Part(p.file, f @ p.matrix, p.material, p.clip)
            owner[pname] = name
        horns.update({h: horn._replace(frame=f) for h, horn in sub.horns.items()})
    if doc.endswith("-plain"):  # the Skeleton plain (#704): each part that has a plain style drawn in it
        from model.printed import styled  # here: model.printed imports what imports this module

        parts = {n: p._replace(file=stl(styled(stem(p.file), plain=True))) for n, p in parts.items()}
    riders = {}  # carrier part -> parts clamped to it
    for sub, carrier in RIDES.items():
        if sub in frames:
            riders.setdefault(carrier, []).extend(n for n in parts if owner[n] == sub)
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
    return Doc(doc, parts, horns)


class _Stages(dict):
    def __missing__(self, doc):
        self[doc] = assemble(doc, DOCS[doc])
        return self[doc]


STAGES = _Stages()  # built on first use: a document per DOCS key


def pose(stage, horn_name, deg):
    """Every part's world 4x4 with the horn at `deg` (degrees from neutral about its pivot axis) and the driven
    joint angles. Raises linkage.Unreachable when a loop cannot close."""
    horn = stage.horns[horn_name]
    mats = {name: p.matrix for name, p in stage.parts.items()}
    f, f_inv = horn.frame, np.linalg.inv(horn.frame)  # the chain solves in its sub-assembly's frame

    def move(name, delta):
        mats[name] = f @ delta @ f_inv @ mats[name]

    move(horn.crank, linkage.rotation(horn.pivot["axis"], deg, horn.pivot["point"]))
    joints, coupled = {j: 0.0 for j in horn.still}, set()
    for loop in horn.loops:
        rocker, a, b = loop.solve(deg)
        _, a0, b0 = loop.solve(0)
        axis = loop.rocker_pivot[1]
        twist = _angle(axis, np.subtract(b, a)) - _angle(axis, np.subtract(b0, a0))
        if loop.coupler not in coupled:  # a coupler driving two rockers (the next Mech's tie-bar) moves once
            coupled.add(loop.coupler)
            move(loop.coupler, linkage.rotation(axis, math.degrees(twist), a) @ translate(np.subtract(a, a0)))
        turn = linkage.rotation(axis, rocker, loop.rocker_pivot[0])
        for name in loop.rockers:
            move(name, turn)
        joints[loop.joint] = round(rocker, 2)
    return Pose(mats, joints)


def _angle(axis, v):
    u, w = linkage._PLANE[tuple(axis)]
    return math.atan2(v[w], v[u])
