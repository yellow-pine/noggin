"""Our geometry as files: every printed part (printed.PARTS, by our part name), every Coupon (printed.COUPONS) and
every hardware envelope (envelopes.ENVELOPES, by the hardware's name), each in its designed frame. `just ours`: all of
them as STLs in model/build/ours (stages.OURS), which MuJoCo (just sim, everywhere) and the renders read, and then the
realistic Skeleton's bones Blender finishes round them from the Skeleton scene (model/skeleton, docs/adr/0025). `just stl`:
the printed parts and the Coupons as print-ready STLs in model/build/stl. `just step`: every shape and each document at
neutral (model/stages.py's placements, as one assembly) as STEP files in model/build/step, for FreeCAD. Run it as its
own process before the model reads them: CadQuery's OCCT threads must not be running when a process pool forks."""

import functools
import os
import shutil
import sys

import cadquery as cq
import trimesh
from OCP.gp import gp_Trsf

from model import envelopes, geometry, printed, skeleton, stages
from model.render import scene

SHAPES = {**printed.PARTS, **printed.COUPONS, **envelopes.ENVELOPES}
PRINTS = [*printed.PARTS, *printed.COUPONS]  # what `just stl` writes
BUILD = os.path.join(stages.REPO, "model", "build")


def export(stem, path):
    """The shape as an STL or STEP (by extension) at `path` (returned), tessellated to 0.02 mm."""
    cq.exporters.export(SHAPES[stem](), path, tolerance=0.02, angularTolerance=0.1)
    return path


def printable(stem, path):
    """The part's STL at `path` (returned) without the zero-area facets OCCT leaves at sphere poles: watertight."""
    mesh = trimesh.load(export(stem, path), force="mesh")
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.export(path)
    return path


def stage_step(doc, path):
    """The document at neutral as one STEP assembly at `path` (returned): every part's shape at its placement (model/stages.py),
    in its Theme's colour (or the hardware's grey). The skull's bones are meshes (geometry.BONES): their STLs alone."""
    shape = functools.cache(lambda stem: SHAPES[stem]())
    asm = cq.Assembly(name=doc)
    for name, part in stages.STAGES[doc].parts.items():
        stem = stages.stem(part.file)
        if stem in geometry.BONES:
            continue
        trsf = gp_Trsf()
        trsf.SetValues(*part.matrix[:3].flatten().tolist())
        loc = cq.Location(trsf)
        asm.add(shape(stem), name=name, loc=loc, color=cq.Color(scene.colour(part.file, geometry.theme(doc))))
    asm.export(path)
    return path


def write(folder, stems, ext, how=export):
    os.makedirs(folder, exist_ok=True)
    for stem in stems:
        how(stem, os.path.join(folder, stem + ext))
    print(f"{len(stems)} shapes in {os.path.relpath(folder, stages.REPO)}")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "ours"
    if what == "ours":
        write(stages.OURS, list(SHAPES), ".stl")
        if shutil.which(skeleton.BLENDER):
            skeleton.finish()  # round the parts just written
            print(f"{len(geometry.BONES)} bones in {os.path.relpath(stages.OURS, stages.REPO)}")
        else:  # the GX10 (#936): no Linux ARM64 Blender; a stale bone would pass tests it should skip
            for stem in geometry.BONES:
                if os.path.exists(stages.stl(stem)):
                    os.remove(stages.stl(stem))
            print(f"no Blender at {skeleton.BLENDER}: the bones are left unfinished, CI finishes them")
    elif what == "stl":
        write(os.path.join(BUILD, "stl"), PRINTS, ".stl", printable)
    elif what == "step":
        write(os.path.join(BUILD, "step"), list(SHAPES), ".step")
        for doc in geometry.STAGES:
            print(stage_step(doc, os.path.join(BUILD, "step", doc + ".step")))
    else:
        sys.exit("usage: python -m model.ours [ours|stl|step]")
