"""Our own printed parts (#50): independent parametric CadQuery designs, by our part name (GLOSSARY.md)."""

import functools

from model.geometry import MECHANICAL
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
    **{stem: PARTS[stem] for stem in ("next torso", "next board rack", "next test stand")},
}
# the Skeleton's parts drawn mechanical alone, with why
UNSTYLED = {"next eyeball core": "the eyeball's ball under its cap: none"}
PARTS |= {stem + MECHANICAL: functools.partial(build, mechanical=True) for stem, build in STYLED.items()}


def carved(build):
    """`build`'s Bones carved from its mechanical part (#809): they never add to it, so its interfaces and
    every clearance stay the mechanical part's."""

    def draw(mechanical=False):
        mech = build(mechanical=True)
        if mechanical:
            return mech
        out = build().intersect(mech)
        assert out.val().isValid() and len(out.val().Solids()) == 1, build
        return out

    return draw


# the parts #708 drew as Bones, carved so
for stem in (
    *("next gimbal frame", "next pitch bar", "next neck mount", "next pan yoke", "next head mount", "next jaw"),
    *("next pan bar", "next tilt bar", "next jaw bar", "next board rack"),
):
    PARTS[stem] = STYLED[stem] = carved(STYLED[stem])


def styled(stem, mechanical):
    """The part `stem` in a style: its mechanical name where it has one (STYLED), else itself."""
    return stem + MECHANICAL if mechanical and stem in STYLED else stem


# test pieces we print to find a fit, not parts of the Mech (GLOSSARY.md Coupon)
COUPONS = {"clearance coupon": coupon.build}
