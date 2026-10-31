"""Our geometry as STLs (`make ours`): every printed part (printed.PARTS, by the designer's STL stem) and every hardware
envelope (envelopes.ENVELOPES, by the STEP mesh's name) in model/build/ours (stages.OURS), each in the frame of the mesh
it stands in for. The engine (make sim, everywhere) and the renders read them. Run it as its
own process before the engine: CadQuery's OCCT threads must not be running when the sweep forks its workers."""

import os

import cadquery as cq

from model import envelopes, printed
from model.engine import stages

SHAPES = {**printed.PARTS, **envelopes.ENVELOPES}


def export(stem, path):
    """The shape as an STL at `path` (returned), tessellated well under the gate's 0.3 mm."""
    cq.exporters.export(SHAPES[stem](), path, tolerance=0.02, angularTolerance=0.1)
    return path


if __name__ == "__main__":
    os.makedirs(stages.OURS, exist_ok=True)
    for stem in SHAPES:
        export(stem, os.path.join(stages.OURS, stem + ".stl"))
    print(f"{len(SHAPES)} shapes in {os.path.relpath(stages.OURS, stages.REPO)}")
