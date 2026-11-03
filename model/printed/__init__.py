"""Our own printed parts (#50): independent parametric CadQuery designs, by our part name (GLOSSARY.md)."""

import functools

from model import skin as sk
from model.geometry import MECHANICAL
from model.printed import base, coupon, gimbal, neck, skin

PARTS = {
    # the next Mech's eye gimbal (#630)
    "next eyeball core": gimbal.core,
    "next L eyeball cap": functools.partial(skin.cap, "L"),  # each Character's largest, Morty's (#665)
    "next R eyeball cap": functools.partial(skin.cap, "R"),
    "next yaw yoke": gimbal.yoke,
    "next tie-bar": gimbal.tie_bar,
    "next bail": gimbal.bail,
    "next push-rod": gimbal.push_rod,
    "next pitch bar": gimbal.pitch_bar,
    "next lid bar": gimbal.lid_bar,
    "next lid link": gimbal.lid_link,
    "next L upper lid": functools.partial(gimbal.upper_lid, "L"),
    "next R upper lid": functools.partial(gimbal.upper_lid, "R"),
    "next L lower lid": functools.partial(gimbal.lower_lid, "L"),
    "next R lower lid": functools.partial(gimbal.lower_lid, "R"),
    "next gimbal frame": gimbal.frame,
    # the next Mech's neck and jaw (#641)
    "next neck mount": neck.mount,
    "next pan yoke": neck.yoke,
    "next head mount": neck.head_mount,
    "next jaw": neck.jaw,
    "next pan bar": neck.pan_bar,
    "next tilt bar": neck.tilt_bar,
    "next jaw bar": neck.jaw_bar,
    # the next Mech's Torso (#685), which carries the Cores (#838)
    "next torso": base.torso,
    # the next Mech's Stage 1 (#720)
    "next test stand": base.stand,
}
# The Skeleton drawn as Bones (#704, #708): each builder's switch `mechanical` draws its mechanical style (#805), the
# same interfaces; PARTS holds it under the stem's mechanical name (geometry.MECHANICAL)
STYLED = {
    **{stem: PARTS[stem] for stem in ("next yaw yoke", "next tie-bar", "next bail", "next push-rod", "next pitch bar")},
    **{stem: PARTS[stem] for stem in ("next lid bar", "next lid link", "next gimbal frame")},
    **{f"next {s} {lid}": PARTS[f"next {s} {lid}"] for s in "LR" for lid in ("upper lid", "lower lid")},
    **{stem: PARTS[stem] for stem in ("next neck mount", "next pan yoke", "next head mount", "next jaw")},
    **{stem: PARTS[stem] for stem in ("next pan bar", "next tilt bar", "next jaw bar")},
    **{stem: PARTS[stem] for stem in ("next torso", "next test stand")},
}
# the Skeleton's parts drawn mechanical alone, with why
UNSTYLED = {"next eyeball core": "the eyeball's ball under its cap: none"}
PARTS |= {stem + MECHANICAL: functools.partial(build, mechanical=True) for stem, build in STYLED.items()}
# Morty's Skin (#665): his Shells, each Seat cut into what carries it in every style (model/skin.py)
PARTS |= {
    "next morty face": skin.face,
    "next morty hair": skin.hair,
    **{f"next morty {s} pupil": functools.partial(skin.pupil, s) for s in "LR"},
    **{
        f"next morty {s} {lid} lid cover": functools.partial(skin.lid_cover, s, lid)
        for s in "LR"
        for lid in ("upper", "lower")
    },
    "next morty mouth cover": skin.mouth_cover,
    **{f"next morty shirt {half}": functools.partial(skin.shirt, half) for half in ("front", "back")},
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
