"""Cable corridors (#49): every lead of the Mech (model/electrical.leads) along a polyline from its first Port through a
few waypoints, each clipped to the part that holds it so it rides pan and tilt, to its second Port. model/mjcf.py makes
each a spatial tendon no longer than the lead (model/test_mjcf.py holds it there across every sweep). Not full cables:
leads are floppy, a corridor is the route the build clips them to."""

import functools

import numpy as np

from model import electrical, stages

# Waypoints per lead (electrical.leads), from its first Port to its second: (part it is clipped to, point in that part's
# sub-assembly frame (eyes frame for the eyes and mouth, PT frame for the base and stack), why). A lead lists its routes
# in order and a document takes the first whose parts it has: the eyes on the neck (stages 2, 3) or on the desk (the
# stem in the base plate's slot: stage 1 and the eyes and mouth documents). Routing from the designer's guides (pan-tilt
# steps 8-10, 13, 17-18: the leads pass under the cable holders and are zip-tied, "make sure this is still sufficient
# length to allow for movement") and the eyes build photos (docs/references/build-photos: the leads leave the servos' backs and
# loop to the keeper and the shield); every point is placed by eye from those photos: inferred.
# On the neck (written in the eyes frame) the head tilts and pans over the stack: the leads leave the servos under the
# servo brackets, clear of the lid servos, gather behind the bracket stem and drop behind the tilt arm between the pan
# bar (-x) and the tilt bar (+x). On the desk (stage 1) they drop off the brackets' feet onto the plate.
UNDER = {
    s: (f"{s} servo bracket:1", (x, -38.5, 28.5), "under the servo bracket, below the lid servo (inferred)")
    for s, x in (("L", -8.5), ("R", 67.5))
}
BEHIND = {
    s: (f"{s} servo bracket:1", (x, -35.5, 49.5), "behind the lid servo, under the bracket's back (inferred)")
    for s, x in (("L", 21.5), ("R", 37.5))
}
GATHER = ("eye bracket:1", (23.5, -38.5, 34.5), "gathered behind the bracket stem, guide step 18 photo (inferred)")
# The eyes build's cable holder on its posts (6, 68.5..92.5), z 13..16: the eye leads pass under it on the plate (Cansin's
# build, docs/references/build-photos/eyes-top.jpg; pan-tilt guide step 18: "Move the original cable hold ... Pass the servo wires
# under the cable holder").
CABLE_HOLDER = (
    "base plate:1",
    (6.0, 80.5, 7.0),
    "under the cable holder, eyes-top build photo and guide step 18 (inferred)",
)
NECK = [
    ("tilt arm:1", (5.5, 36.0, 38.0), "zip-tied behind the tilt arm's back, guide step 18 photo (inferred)"),
    ("upright:1", (5.5, 36.0, 20.0), "down behind the upright, guide step 18 photo (inferred)"),
    CABLE_HOLDER,
]
DESK = {
    s: [
        (
            f"{s} servo bracket:1",
            (x, -34.5, 48.5),
            "off the servo bracket's foot onto the plate, eyes build photos (inferred)",
        ),
        CABLE_HOLDER,
    ]
    for s, x in (("L", 21.5), ("R", 37.5))
}
NECK_START = {
    "l_lid": [BEHIND["L"]],
    "r_lid": [BEHIND["R"], GATHER],
    "l_eye": [UNDER["L"], GATHER],
    "r_eye": [UNDER["R"], GATHER],
}
ROUTES = {
    **{
        f"{servo} servo -> Core 1 PWM{n}": [[*NECK_START[servo], *NECK], DESK[servo[0].upper()]]
        for n, servo in electrical.CHANNELS["core1"].items()
    },
    "tilt servo -> Core 2 PWM1": [
        [("tilt servo:1", (36.0, 32.0, 12.0), "bent down off the tilt servo's cable end, guide step 10 (inferred)")]
    ],
    "mouth servo -> Core 2 PWM2": [
        [
            (*UNDER["R"][:2], "joins the R eye lead under the R servo bracket (inferred)"),
            GATHER,
            *NECK,
        ]
    ],
    "pan servo -> Core 2 PWM3": [
        [("wire holder:1", (-5.0, 40.5, 6.0), "under the cable holder, guide steps 8-9 (inferred)")]
    ],
    # The pack's lead leaves its front end, crosses the plate and runs back up the middle to the switch board's input
    # socket (Cansin's build, docs/references/build-photos/eyes-top.jpg; guide p.23 photo).
    "pack 1 -> switch 1": [
        [
            (
                "base plate:1",
                (-18.0, 66.0, 6.0),
                "out of the pack's front end past the box's front corner, build photo (inferred)",
            ),
            (
                "base plate:1",
                (12.0, 100.0, 6.0),
                "back up the middle of the plate to the switch board, build photo (inferred)",
            ),
        ]
    ],
    # The Y lead leaves the switch board's output over the plate's +x edge and runs along it into each shield's XH socket
    # from +x (Cansin's build for shield 1, the photo's loop; guide p.23 photo for both branches).
    **{
        f"switch 1 -> shield {n}": [
            [
                (
                    "base plate:1",
                    (59.0, 110.0, 4.0),
                    "over the plate's +x edge below the switch board, build photo (inferred)",
                ),
                (
                    "base plate:1",
                    (59.0, y, 4.0),
                    "along the +x edge to the shield, build photo and guide p.23 (inferred)",
                ),
            ]
        ]
        for n, y in ((1, 56.0), (2, 89.0))
    },
}


@functools.cache
def _home():
    """Every part's matrix in its own sub-assembly's frame: where ROUTES' points are written."""
    return {n: p.matrix for build in stages.SUBS.values() for n, p in build().parts.items()}


def local(part, point):
    """A ROUTES point (its part's sub-assembly frame) in the part's own frame."""
    return (np.linalg.inv(_home()[part]) @ np.array([*point, 1.0]))[:3]
