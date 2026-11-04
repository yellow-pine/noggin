"""The Mech as data: its sub-assemblies (every part with its mesh file, neutral placement and material, the horns
and their four-bar chains) built from model/gimbal.py, model/neck.py and model/base.py, and assemble() putting
sub-assemblies at frames into one document (geometry.STAGES, geometry.MECH). pose() gives every part's world transform at a horn angle by
the four-bar kinematics (model/linkage.py), exactly, without simulating. Part names carry a ":1" suffix, as MuJoCo's
bodies and the GLBs' nodes."""

import functools
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
# A rod riding another moving part, the `carrier` (the Mech's pitch push-rods on the bail, #663; each lower lid's
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


def base_sub():
    """base: the Mech's Torso (#685, model/base.py) with the pack lying across x on its floor, its lead out to
    -x, the switch board lying beside the lead's end (#828) and the power-path board in front of the neck (#858), the
    same in every head variant."""
    pack = align((candidates.PACK[0] / 2, candidates.PACK_Y, neck.MOUNT_Z[0] - g.BATTERY_STEP["floor_z"]), g.Y)
    parts = {
        "torso:1": part(stl("torso"), None, printed("torso")),
        "torso lid:1": part(stl("torso lid"), None, printed("torso lid")),
        "pack:1": part(stl("battery"), pack, BOARD, ("y", g.BATTERY_STEP["lead_y"])),
    }
    boards = candidates.switch_board() | candidates.power_board()
    parts |= {f"{name}:1": part(stl(mesh), at, BOARD) for name, (mesh, at) in boards.items()}
    return Sub(parts, {})


def cranium_sub():
    """cranium: the boards in the Mech's head (#858, model/base.py): the cranium tray on the gimbal frame's
    plate, both Cores lying on it, each under its Shield, and the hub on its riser; it rides the head (RIDES)."""
    return _boards("cranium tray", candidates.cranium())


def _boards(stem, placed):
    """The carrier's part and the boards on it, placed (model/base.py)."""
    parts = {f"{stem}:1": part(stl(stem), None, printed(stem))}
    parts |= {f"{name}:1": part(stl(mesh), at, BOARD) for name, (mesh, at) in placed.items()}
    return Sub(parts, {})


def eyes_sub():
    """eyes: the Mech's eye gimbal (#630, model/gimbal.py) at rest, in its own frame: per eye the core, its
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
            ("eyeball core", "eyeball core", at),
            ("eyeball cap", f"{s} eyeball cap", at),
            ("yaw yoke", "yaw yoke", at),
            ("push-rod", "push-rod", translate((cx, 0, 0))),
            ("upper lid", f"{s} upper lid", at),
            ("lower lid", f"{s} lower lid", at),
            ("lid bar", "lid bar", translate((cx - sign * sum(gimbal.LID_X["bar"]) / 2, 0, 0))),
            ("lid link", "lid link", translate((cx - sign * sum(gimbal.LID_X["link"]) / 2, 0, 0))),
        ):
            parts[f"{s} {name}:1"] = part(stl(stem), m, printed(stem))
    for stem in ("tie-bar", "bail", "pitch bar", "gimbal frame"):
        parts[stem + ":1"] = part(stl(stem), None, printed(stem))
    for label, (face, shaft, tab, arm) in gimbal.drives().items():
        parts.update(mounted(gimbal.servo_origin(face, shaft), tab, shaft, label, arm))
    lo, hi = (gimbal.servos(0, p)[1] for p in (gimbal.PITCH, -gimbal.PITCH))
    limits = {
        "yaw": (-gimbal.YAW, gimbal.YAW),
        "pitch": (lo, hi),
        "lid": tuple(e - gimbal.LID_REST for e in gimbal.LID_EDGES),
    }
    crank = gimbal.CRANK
    yaw = (0.0, gimbal.YAW_Y, gimbal.TIE_Z[1])  # the tie-bar's plane, under the yokes' cranks
    horns["yaw horn"] = Horn(
        {"point": yaw, "axis": g.Z},
        limits["yaw"],
        "yaw horn:1",
        [
            rocker_loop(
                f"{s} yaw pivot",
                yaw,
                (0.0, gimbal.YAW_Y + crank, yaw[2]),
                (x, 0.0, yaw[2]),
                (x, crank, yaw[2]),
                g.Z,
                "tie-bar:1",
                [f"{s} {p}:1" for p in ("yaw yoke", "eyeball core", "eyeball cap")],
            )
            for s, (x, _, _) in gimbal.EYE.items()
        ],
        [],
        None,
    )
    horn, bail = (0.0, *gimbal.PITCH_HORN), (0.0, *gimbal.BAIL)
    horns["pitch horn"] = Horn(
        {"point": horn, "axis": g.X},
        limits["pitch"],
        "pitch horn:1",
        [
            rocker_loop(
                "bail pivot",
                horn,
                (0.0, horn[1] + crank, horn[2]),
                bail,
                (0.0, bail[1] + gimbal.BAIL_IN, bail[2]),
                g.X,
                "pitch bar:1",
                ["bail:1"],
            )
        ],
        [],
        None,
        [
            Rod(
                f"{s} push-rod",
                f"{s} push-rod:1",
                "bail:1",
                (x, bail[1], bail[2] + gimbal.LEVER),
                (g.X, g.Z),
                (f"{s} eyeball pitch", (x, 0.0, 0.0), (-1, 0, 0)),  # pitch up positive, as gimbal.core
                [f"{s} eyeball core:1", f"{s} eyeball cap:1"],
                (x, 0.0, gimbal.LEVER),
            )
            for s, (x, _, _) in gimbal.EYE.items()
        ],
    )
    for s, (x, _, _) in gimbal.EYE.items():  # lid servo positive opens: about -x, as gimbal.moved
        horn = (x, *gimbal.LID_HORN)
        horns[f"{s} lid horn"] = Horn(
            {"point": horn, "axis": (-1, 0, 0)},
            limits["lid"],
            f"{s} lid horn:1",
            [
                rocker_loop(
                    f"{s} lid pivot",
                    horn,
                    (x, *np.add(gimbal.LID_HORN, gimbal.LID_PIN)),
                    (x, 0.0, 0.0),
                    (x, *gimbal.LID_PIN),
                    (-1, 0, 0),
                    f"{s} lid bar:1",
                    [f"{s} upper lid:1"],
                )
            ],
            [],
            None,
            [
                Rod(
                    f"{s} lid link",
                    f"{s} lid link:1",
                    f"{s} lid bar:1",
                    (x, *gimbal.LINK_PIN),
                    (-1, 0, 0),
                    (f"{s} lower lid pivot", (x, 0.0, 0.0), (-1, 0, 0)),  # up positive, as gimbal.lower
                    [f"{s} lower lid:1"],
                    (x, *gimbal.LOWER_PIN),
                )
            ],
        )
    return Sub(parts, horns)


def _neck_drives(labels, drives, stems):
    """(parts, horns): the neck Core's drives of `drives` (pan, tilt, jaw) with their servos (`labels`) and the printed
    `stems`, at rest in the head's frame (model/neck.py). Each drive turns its horn so the MuJoCo report and the Core's
    servo names apply (#642): the pan carries the yoke and the head, the tilt the head (neck.HEAD, those of its parts
    the document has, and what rides the head mount: RIDES), the mouth the jaw."""
    parts = {f"{stem}:1": part(stl(stem), None, printed(stem)) for stem in stems}
    for label, (face, shaft, tab, arm) in neck.drives().items():
        if label in labels:
            parts.update(mounted(gimbal.servo_origin(face, shaft), tab, shaft, label, arm))
    pins, head = neck.pins(), list(neck.HEAD)
    carried = {
        "pan": ["pan yoke:1", "tilt servo:1", "tilt horn:1", "tilt bar:1", *head],
        "tilt": head,
        "jaw": ["jaw:1"],
    }
    horns = {}
    for drive, crank, horn, bar in (
        ("pan", "pan horn:1", "pan horn", "pan bar:1"),
        ("tilt", "tilt horn:1", "tilt horn", "tilt bar:1"),
        ("jaw", "mouth horn:1", "jaw horn", "jaw bar:1"),
    ):
        if drive in drives:
            o4, _, o2, axis = pins[drive]
            loop = Loop(f"{drive} pivot", neck.LINKAGES[drive], bar, carried[drive], (tuple(o4), tuple(axis)))
            ends = sorted(neck.servo_for(drive, d) if d else 0.0 for d in neck.RANGES[drive])
            still = [f"{d} pivot" for d in ("pan", "tilt") if d != drive]  # the jaw rides them both
            horns[horn] = Horn({"point": o2, "axis": axis}, tuple(ends), crank, [loop], still, None)
    return Sub(parts, horns)


def neck_sub():
    """neck: the Mech's neck (#641, model/neck.py) at rest, in the head's frame (the gimbal's): the neck mount,
    the pan yoke, the head mount and the pan and tilt bars, the neck Core's pan and tilt servos with their horns on the
    drives."""
    stems = ("neck mount", "pan yoke", "head mount", "pan bar", "tilt bar")
    return _neck_drives(("pan", "tilt"), ("pan", "tilt"), stems)


def jaw_sub():
    """jaw: the Mech's jaw (#641, model/neck.py) at rest, in the head's frame: the jaw and its bar, the mouth
    servo with its horn on the drive; it rides the head (RIDES)."""
    return _neck_drives(("mouth",), ("jaw",), ("jaw", "jaw bar"))


def stand_sub():
    """stand: Stage 1's test stand (#720, model/base.py) under the gimbal frame's plate, the eyes Core upright on
    its back face."""
    return _boards("test stand", candidates.stand_boards())


def skull_sub():
    """skull: the realistic Skeleton's skull (#838; model/skeleton finishes it) as a Skin wears it (g.WORN), its bones
    drawn where they sit at rest in the head's frame, each on what carries it (RIDES): the skull on the gimbal frame,
    the mandible on the jaw, the atlas and the axis on the pan yoke."""
    return Sub({f"{stem}:1": part(stl(stem), None, printed(stem)) for stem in (g.WORN.get(s, s) for s in g.SKULL)}, {})


def skin_sub(skin):
    """next-<skin>: a Skin (g.SKINS: Morty's, #665; Cansin's, #813; model/skin.py), each Shell where it sits on what
    carries it (RIDES): the face and the hair on the head, a pupil in each cap, a cover on each lid, the mouth cover on
    the jaw, the shirt on the Torso; an eye's own (side) drawn in its frame."""
    parts = {}
    for stem in g.PRINTED:
        if stem.startswith(f"{skin} "):
            side = next((s for s in gimbal.EYE if f" {s} " in stem), None)
            parts[stem + ":1"] = part(stl(stem), side and translate(gimbal.EYE[side]), printed(stem))
    return Sub(parts, {})


SUBS = {
    "eyes": eyes_sub,
    "neck": neck_sub,
    "jaw": jaw_sub,
    "base": base_sub,
    "cranium": cranium_sub,
    "stand": stand_sub,
    **{sub: functools.partial(skin_sub, skin) for skin, sub in g.SKINS.items()},
    g.SKULL_SUB: skull_sub,
}
# The documents the model simulates: {document: {sub-assembly: its frame}}, each frame (origin, x axis, z axis) as
# geometry.align_rows: the Mech's Stages in every Skeleton, the last of them the head variant's (geometry.MECH)
DOCS = g.STAGES | g.MECH | g.DRESSED
RIDES = {
    "eyes": "head mount:1",  # the gimbal frame screwed on its flange
    "jaw": "head mount:1",  # the jaw on its lugs, the mouth servo in its collar
    "cranium": "gimbal frame:1",  # the cranium tray on its plate (#858)
    # a Skin's Shells, each on its Seats (model/skin.py) or glued in its seat (skin.GLUED) on the part that moves it,
    # the shirt (and what it carries) on the Torso, which moves none
    **{
        f"{shell}:1": f"{carrier}:1"
        for skin in g.SKINS
        for shell, carrier in {
            f"{skin} face": "gimbal frame",
            f"{skin} hair": "gimbal frame",
            **{f"{skin} {s} {p}": f"{s} eyeball cap" for s in "LR" for p in ("pupil", "pupil plug")},
            **{f"{skin} {s} {lid} lid cover": f"{s} {lid} lid" for s in "LR" for lid in ("upper", "lower")},
            **{f"{skin} {s} brow": "gimbal frame" for s in "LR"},
            f"{skin} mouth cover": "jaw",
            f"{skin} teeth": "jaw",
        }.items()
        if shell in g.PRINTED
    },
    # the realistic skull's bones (#838), each lying on its carrier
    "skull:1": "gimbal frame:1",
    "mandible:1": "jaw:1",
    "worn skull:1": "gimbal frame:1",
    "worn mandible:1": "jaw:1",
    "atlas:1": "pan yoke:1",
    "axis:1": "pan yoke:1",
}  # clamped to that part (a sub-assembly's every part, or one part)


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
    if doc.endswith("-mechanical"):  # the Skeleton mechanical (#704): each part that has a mechanical style drawn in it
        from model.printed import styled  # here: model.printed imports what imports this module

        parts = {n: p._replace(file=stl(styled(stem(p.file), mechanical=True))) for n, p in parts.items()}
    riders = {}  # carrier part -> parts clamped to it
    for sub, carrier in RIDES.items():
        riders.setdefault(carrier, []).extend(n for n in parts if owner[n] == sub or n == sub)

    def carried(names):
        out, todo = list(names), list(names)
        while todo:  # transitive: a carried part may carry more
            for n in riders.get(todo.pop(), []):
                if n not in out:
                    out.append(n)
                    todo.append(n)
        return [n for n in out if n in parts]  # the Stage's own

    for h, horn in horns.items():
        loops = [loop._replace(rockers=carried(loop.rockers)) for loop in horn.loops]
        horns[h] = horn._replace(loops=loops, rods=[rod._replace(driven=carried(rod.driven)) for rod in horn.rods])
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
        if loop.coupler not in coupled:  # a coupler driving two rockers (the Mech's tie-bar) moves once
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
