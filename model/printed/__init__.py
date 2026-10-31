"""Our own printed parts (#50): independent parametric CadQuery designs, by the designer's STL stem each stands in for."""

import cadquery as cq

from model.printed import (
    bars,
    base,
    bearing_block,
    bottom_jaw,
    jaws_connector_bar,
    jaws_servo_mount,
    main_bracket,
    pan_base,
    servo_mount,
    tilt_arm,
    top_jaw,
    upright,
    wire_holder,
)

PARTS = {
    "main bracket v2": main_bracket.build,
    "jaws servo mount": jaws_servo_mount.build,
    "jaws connector bar": jaws_connector_bar.build,
    "top jaw plain": top_jaw.build,
    "bottom jaw plain": bottom_jaw.build,
    "tilt bar": bars.tilt,
    "PandT bar": bars.pan,
    "PandT bearing block": bearing_block.build,
    "PandT servo mount plain": servo_mount.plain,
    "PandT servo mount cutout": servo_mount.cutout,
    "PandT wire holder": wire_holder.build,
    "PandT pan base": pan_base.build,
    "PandT upright v2": upright.build,
    "PandT tilt arm": tilt_arm.build,
    "PandT base": base.build,
}


def export(stem, path):
    """The part as an STL at `path` (returned) in its designer's frame, tessellated well under the gate's 0.3 mm."""
    cq.exporters.export(PARTS[stem](), path, tolerance=0.02, angularTolerance=0.1)
    return path
