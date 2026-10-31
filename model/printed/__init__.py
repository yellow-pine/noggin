"""Our own printed parts (#50): independent parametric CadQuery designs, by the designer's STL stem each stands in for."""

import cadquery as cq

from model.printed import bars, bearing_block, main_bracket, pan_base, servo_mount, wire_holder

PARTS = {
    "main bracket v2": main_bracket.build,
    "tilt bar": bars.tilt,
    "PandT bar": bars.pan,
    "PandT bearing block": bearing_block.build,
    "PandT servo mount plain": servo_mount.plain,
    "PandT servo mount cutout": servo_mount.cutout,
    "PandT wire holder": wire_holder.build,
    "PandT pan base": pan_base.build,
}


def export(stem, path):
    """The part as an STL at `path` (returned) in its designer's frame, tessellated well under the gate's 0.3 mm."""
    cq.exporters.export(PARTS[stem](), path, tolerance=0.02, angularTolerance=0.1)
    return path
