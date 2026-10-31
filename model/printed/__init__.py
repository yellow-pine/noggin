"""Our own printed parts (#50): independent parametric CadQuery designs, by the designer's STL stem each stands in for."""

import cadquery as cq

from model.printed import eyeball, eyeball_bar, eyelid_bar, lid, main_bracket, pupil, servo_bracket

PARTS = {
    "main bracket v2": main_bracket.build,
    "eyelid bar": eyelid_bar.build,
    "eyelid bar crank": eyelid_bar.crank,
    "eyeball bar": eyeball_bar.build,
    "regular pupil": pupil.build,
    "L eyeball regular": lambda: eyeball.build("L"),
    "R eyeball regular": lambda: eyeball.build("R"),
    "inside lid": lambda: lid.build("inside"),
    "outside lid": lambda: lid.build("outside"),
    "L servo bracket": lambda: servo_bracket.build("L"),
    "R servo bracket": lambda: servo_bracket.build("R"),
}


def export(stem, path):
    """The part as an STL at `path` (returned) in its designer's frame, tessellated well under the gate's 0.3 mm."""
    cq.exporters.export(PARTS[stem](), path, tolerance=0.02, angularTolerance=0.1)
    return path
