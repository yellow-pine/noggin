"""Our own printed parts (#50): independent parametric CadQuery designs, by the designer's STL stem each stands in for."""

import cadquery as cq

from model.printed import bottom_jaw, jaws_connector_bar, jaws_servo_mount, main_bracket, top_jaw

PARTS = {
    "main bracket v2": main_bracket.build,
    "jaws servo mount": jaws_servo_mount.build,
    "jaws connector bar": jaws_connector_bar.build,
    "top jaw plain": top_jaw.build,
    "bottom jaw plain": bottom_jaw.build,
}


def export(stem, path):
    """The part as an STL at `path` (returned) in its designer's frame, tessellated well under the gate's 0.3 mm."""
    cq.exporters.export(PARTS[stem](), path, tolerance=0.02, angularTolerance=0.1)
    return path
