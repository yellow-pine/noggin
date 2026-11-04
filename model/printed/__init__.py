"""Our own printed parts (#50): independent parametric CadQuery designs, by our part name (GLOSSARY.md)."""

import functools

from model import skin as sk
from model.geometry import BONES, MECHANICAL, SKINS
from model.printed import base, coupon, gimbal, neck, skin

PARTS = {
    # the Mech's eye gimbal (#630)
    "eyeball core": gimbal.core,
    "L eyeball cap": functools.partial(skin.cap, "L"),  # each Character's largest, Morty's (#665)
    "R eyeball cap": functools.partial(skin.cap, "R"),
    "yaw yoke": gimbal.yoke,
    "tie-bar": gimbal.tie_bar,
    "bail": gimbal.bail,
    "push-rod": gimbal.push_rod,
    "pitch bar": gimbal.pitch_bar,
    "lid bar": gimbal.lid_bar,
    "lid link": gimbal.lid_link,
    "L upper lid": functools.partial(gimbal.upper_lid, "L"),
    "R upper lid": functools.partial(gimbal.upper_lid, "R"),
    "L lower lid": functools.partial(gimbal.lower_lid, "L"),
    "R lower lid": functools.partial(gimbal.lower_lid, "R"),
    "gimbal frame": gimbal.frame,
    # the Mech's neck and jaw (#641)
    "cervical carrier": neck.cervical_carrier,
    "nod plate": neck.nod_plate,
    "head mount": neck.head_mount,
    "jaw": neck.jaw,
    "jaw bar": neck.jaw_bar,
    "tilt lever": neck.tilt_lever,
    "tilt reaction bar": neck.tilt_reaction_bar,
    # the Mech's Torso (#685) and the cranium tray, which carries the Cores in the head (#858)
    "torso": base.torso,
    "torso lid": base.lid,
    "cranium tray": base.tray,
    # the Mech's Stage 1 (#720)
    "test stand": base.stand,
}
# The Skeleton drawn as Bones (#704, #708): each builder's switch `mechanical` draws its mechanical style (#805), the
# same interfaces; PARTS holds it under the stem's mechanical name (geometry.MECHANICAL)
STYLED = {
    **{stem: PARTS[stem] for stem in ("yaw yoke", "tie-bar", "bail", "push-rod", "pitch bar")},
    **{stem: PARTS[stem] for stem in ("lid bar", "lid link", "gimbal frame")},
    **{f"{s} {lid}": PARTS[f"{s} {lid}"] for s in "LR" for lid in ("upper lid", "lower lid")},
    **{stem: PARTS[stem] for stem in ("jaw", "jaw bar")},
    **{stem: PARTS[stem] for stem in ("torso", "torso lid", "test stand")},
}
# the Skeleton's parts drawn mechanical alone, with why
UNSTYLED = {
    "eyeball core": "the eyeball's ball under its cap: none",
    "cranium tray": "hidden in the realistic skull's cranium: none (#858)",
    **dict.fromkeys(
        ("cervical carrier", "nod plate", "head mount", "tilt lever", "tilt reaction bar"),
        "hidden structural bearing and servo interfaces (#902)",
    ),
} | dict.fromkeys(
    BONES,
    "the realistic Skeleton's skull, a mesh (the Skeleton scene, model/skeleton): the mechanical Skeleton has none (#838)",
)
PARTS |= {stem + MECHANICAL: functools.partial(build, mechanical=True) for stem, build in STYLED.items()}
# The Skins (#665, #813): each one's Shells, each Seat cut into what carries it in every style (model/skin.py)
for _skin in SKINS:
    PARTS |= {
        f"{_skin} face": functools.partial(skin.face, _skin),
        f"{_skin} hair": functools.partial(skin.hair, _skin),
        **{
            f"{_skin} {s} {lid} lid cover": functools.partial(skin.lid_cover, _skin, s, lid)
            for s in "LR"
            for lid in ("upper", "lower")
        },
        f"{_skin} mouth cover": functools.partial(skin.mouth_cover, _skin),
        **{f"{_skin} shirt {half}": functools.partial(skin.shirt, _skin, half) for half in ("front", "back")},
    }
PARTS |= {
    **{f"morty {s} pupil": functools.partial(skin.pupil, s) for s in "LR"},
    **{f"{k} {s} pupil plug": functools.partial(skin.pupil_plug, s) for k in sk.DOTTED for s in "LR"},
    **{f"{k} {s} pupil": functools.partial(skin.dot, s) for k in sk.DOTTED for s in "LR"},
    **{f"cansin {s} brow": functools.partial(skin.brow, s) for s in "LR"},
    "cansin teeth": skin.teeth,
    "cansin sunglasses": skin.sunglasses,
}
PARTS |= {
    stem: skin.seated(stem, build)
    for stem, build in PARTS.items()
    if stem.removesuffix(MECHANICAL) in {s.carrier for s in sk.SEATS} and stem not in sk.SHELLS
}


def styled(stem, mechanical):
    """The part `stem` in a style: its mechanical name where it has one (STYLED), else itself."""
    return stem + MECHANICAL if mechanical and stem in STYLED else stem


# test pieces we print to find a fit, not parts of the Mech (GLOSSARY.md Coupon)
COUPONS = {"clearance coupon": coupon.build}
