"""Our own printed parts (#50): independent parametric CadQuery designs, by the designer's STL stem each stands in for."""

import cadquery as cq

from model.printed import bars, main_bracket

PARTS = {"main bracket v2": main_bracket.build, "tilt bar": bars.tilt, "PandT bar": bars.pan}


def export(stem, path):
    """The part as an STL at `path` (returned) in its designer's frame, tessellated well under the gate's 0.3 mm."""
    cq.exporters.export(PARTS[stem](), path, tolerance=0.02, angularTolerance=0.1)
    return path
