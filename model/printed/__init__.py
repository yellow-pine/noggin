"""Our own printed parts (#50): independent parametric CadQuery designs, by our part name (GLOSSARY.md), and the
features each declares for the mating check (model/mating.py)."""

import functools

from model.geometry import PLAIN
from model.printed import (
    bars,
    base,
    base_plate,
    bearing_block,
    bottom_jaw,
    coupon,
    eye_bracket,
    eyeball,
    eyeball_bar,
    gimbal,
    jaw_bar,
    jaw_servo_mount,
    lid,
    lid_bar,
    neck,
    pan_servo_mount,
    pan_turntable,
    pupil,
    servo_bracket,
    tilt_arm,
    top_jaw,
    upright,
    wire_holder,
    wire_keeper,
)

PARTS = {
    "eye bracket": eye_bracket.build,
    "desk eye bracket": lambda: eye_bracket.build(desk=True),
    "lid bar": lid_bar.build,
    "lid crank": lid_bar.crank,
    "eyeball bar": eyeball_bar.build,
    "pupil": pupil.build,
    "L eyeball": lambda: eyeball.build("L"),
    "R eyeball": lambda: eyeball.build("R"),
    "upper lid": lambda: lid.build("upper"),
    "lower lid": lambda: lid.build("lower"),
    "L servo bracket": lambda: servo_bracket.build("L"),
    "R servo bracket": lambda: servo_bracket.build("R"),
    "jaw servo mount": jaw_servo_mount.build,
    "jaw bar": jaw_bar.build,
    "top jaw": top_jaw.build,
    "bottom jaw": bottom_jaw.build,
    "tilt bar": bars.tilt,
    "pan bar": bars.pan,
    "bearing block": bearing_block.build,
    "pan servo tail mount": pan_servo_mount.tail,
    "pan servo lead mount": pan_servo_mount.lead,
    "wire holder": wire_holder.build,
    "pan turntable": pan_turntable.build,
    "upright": upright.build,
    "tilt arm": tilt_arm.build,
    "base plate": base_plate.build,
    "wire keeper": wire_keeper.build,
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
    "next L lid": lambda: gimbal.lid("L"),
    "next R lid": lambda: gimbal.lid("R"),
    "next gimbal frame": gimbal.frame,
    # the next Mech's neck and jaw (#641)
    "next neck mount": neck.mount,
    "next pan yoke": neck.yoke,
    "next head mount": neck.head_mount,
    "next jaw": neck.jaw,
    "next pan bar": neck.pan_bar,
    "next tilt bar": neck.tilt_bar,
    "next jaw bar": neck.jaw_bar,
    # the next Mech's Torso (#685) and its head variants' board carriers (#686)
    "next torso": base.torso,
    "next board rack": base.rack,
    "next crown shelf": base.crown_shelf,
    "next split shelf": base.split_shelf,
    "next switch bracket": base.switch_bracket,
}
# The Skeleton drawn as Bones (#704): each builder's switch `plain` draws its plain style, the same interfaces; PARTS
# holds it under the stem's plain name (geometry.PLAIN)
STYLED = {
    "next yaw yoke": gimbal.yoke,
    "next tie-bar": gimbal.tie_bar,
    "next bail": gimbal.bail,
    "next push-rod": gimbal.push_rod,
    "next torso": base.torso,
    "next board rack": base.rack,
}
# the Skeleton's parts drawn plain alone: their Bones wait on the ticket reshaping them, which draws both styles
UNSTYLED = {
    "next eyeball core": "the eyeball's ball under its cap: none",
    **dict.fromkeys(("next L lid", "next R lid", "next lid bar", "next pitch bar", "next gimbal frame"), "#698"),
    **dict.fromkeys(
        ("next neck mount", "next pan yoke", "next head mount", "next jaw", "next pan bar", "next tilt bar"), "#708"
    ),
    **dict.fromkeys(("next jaw bar", "next crown shelf", "next split shelf", "next switch bracket"), "#708"),
}
PARTS |= {stem + PLAIN: functools.partial(build, plain=True) for stem, build in STYLED.items()}


def styled(stem, plain):
    """The part `stem` in a style: its plain name where it has one (STYLED), else itself."""
    return stem + PLAIN if plain and stem in STYLED else stem


# test pieces we print to find a fit, not parts of the Mech (GLOSSARY.md Coupon)
COUPONS = {"clearance coupon": coupon.build}
FEATURES = {
    "eye bracket": eye_bracket.features(),
    "desk eye bracket": eye_bracket.features(desk=True),
    "lid bar": lid_bar.features(),
    "lid crank": lid_bar.features(crank=True),
    "eyeball bar": eyeball_bar.features(),
    "L eyeball": eyeball.features("L"),
    "R eyeball": eyeball.features("R"),
    "upper lid": lid.features("upper"),
    "lower lid": lid.features("lower"),
    "L servo bracket": servo_bracket.features("L"),
    "R servo bracket": servo_bracket.features("R"),
    "jaw servo mount": jaw_servo_mount.features(),
    "jaw bar": jaw_bar.features(),
    "top jaw": top_jaw.features(),
    "bottom jaw": bottom_jaw.features(),
    "tilt bar": bars.features(bars.TILT_PITCH),
    "pan bar": bars.features(bars.PAN_PITCH),
    "pan servo tail mount": pan_servo_mount.features(pan_servo_mount.TAIL),
    "pan servo lead mount": pan_servo_mount.features(pan_servo_mount.LEAD),
    "pan turntable": pan_turntable.features(),
    "upright": upright.features(),
    "tilt arm": tilt_arm.features(),
    "base plate": base_plate.features(),
}
