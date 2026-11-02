"""Our own printed parts (#50): independent parametric CadQuery designs, by our part name (GLOSSARY.md)."""

import functools

from model.geometry import PLAIN
from model.printed import base, coupon, gimbal, neck

PARTS = {
    # the next Mech's eye gimbal (#630)
    "next eyeball core": gimbal.core,
    "next L eyeball cap": lambda: gimbal.cap("L"),
    "next R eyeball cap": lambda: gimbal.cap("R"),
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
    # the next Mech's Torso (#685) and its head variant's board carrier (#686, Back alone since #712)
    "next torso": base.torso,
    "next board rack": base.rack,
}
# The Skeleton drawn as Bones (#704): each builder's switch `plain` draws its plain style, the same interfaces; PARTS
# holds it under the stem's plain name (geometry.PLAIN)
STYLED = {
    "next yaw yoke": gimbal.yoke,
    "next tie-bar": gimbal.tie_bar,
    "next bail": gimbal.bail,
    "next push-rod": gimbal.push_rod,
    **{stem: PARTS[stem] for stem in ("next lid bar", "next lid link")},
    **{f"next {s} {lid}": PARTS[f"next {s} {lid}"] for s in "LR" for lid in ("upper lid", "lower lid")},
    "next torso": base.torso,
    "next board rack": base.rack,
}
# the Skeleton's parts drawn plain alone: their Bones wait on the ticket reshaping them, which draws both styles
UNSTYLED = {
    "next eyeball core": "the eyeball's ball under its cap: none",
    **dict.fromkeys(("next pitch bar", "next gimbal frame"), "#704"),
    **dict.fromkeys(
        (
            "next neck mount",
            "next pan yoke",
            "next head mount",
            "next jaw",
            "next pan bar",
            "next tilt bar",
            "next jaw bar",
        ),
        "#708",
    ),
}
PARTS |= {stem + PLAIN: functools.partial(build, plain=True) for stem, build in STYLED.items()}


def styled(stem, plain):
    """The part `stem` in a style: its plain name where it has one (STYLED), else itself."""
    return stem + PLAIN if plain and stem in STYLED else stem


# test pieces we print to find a fit, not parts of the Mech (GLOSSARY.md Coupon)
COUPONS = {"clearance coupon": coupon.build}
