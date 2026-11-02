"""Our own printed parts (#50): independent parametric CadQuery designs, by our part name (GLOSSARY.md)."""

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
    # the next Mech's Torso (#685) and its head variant's board carrier (#686, Back alone since #712)
    "next torso": base.torso,
    "next board rack": base.rack,
}
# test pieces we print to find a fit, not parts of the Mech (GLOSSARY.md Coupon)
COUPONS = {"clearance coupon": coupon.build}
