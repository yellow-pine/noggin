"""Tessellate the Bambu STEP files into model/build/steps/<key>.stl in their STEP-local frames (the STLs shipped
beside the STEPs sit on a print plate, not in the frame geometry.py measures). Run: `make model-step-meshes`
(uv run --with cadquery-ocp, no project dependency). The receiver is split into shield and Core (the Core's solids
lie under the PCB, local y < 0) and the battery lead is dropped (solids beyond BATTERY_STEP lead_y), as the Fusion builds do."""

import os
import struct

import numpy as np
from OCP.Bnd import Bnd_Box
from OCP.BRep import BRep_Tool
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAD = os.path.join(REPO, "docs/references/cyberbrick-cad")
SERVO_DIR = os.path.join(CAD, "servo/CAD_9g Servo Motor with Clutch Protection-PG002-PG001")
STEP = {
    "servo": os.path.join(SERVO_DIR, "9g Servo Motor with Clutch Protection-PG002-PG001.stp"),
    "horn": os.path.join(SERVO_DIR, "9g Servo Motor with Clutch Protection-half arm1-PG002-PG001.stp"),
    "receiver": os.path.join(
        CAD, "receiver/Remote Control Receiver-XA003-XA004/Remote Control Receiver-XA003-XA004.stp"
    ),
    "switch": os.path.join(
        CAD,
        "switch/Power Switch Board with 2Pin XH2.54 Connector-XA007/Power Switch Board with 2Pin XH2.54 Connector-XA007.STEP",
    ),
    "battery": os.path.join(
        CAD, "battery/14500 7.4V 800mAh Li-ion Battery-PC003/14500 7.4V 800mAh Li-ion Battery-PC003.stp"
    ),
}
OUT = os.path.join(REPO, "model", "build", "steps")
DEFLECTION_MM = 0.05
LEAD_Y = 56.0  # geometry.BATTERY_STEP["lead_y"]


def solids(path):
    r = STEPControl_Reader()
    r.ReadFile(path)
    r.TransferRoots()
    shape = r.OneShape()
    BRepMesh_IncrementalMesh(shape, DEFLECTION_MM, False, 0.5, True)
    ex = TopExp_Explorer(shape, TopAbs_SOLID)
    if not ex.More():  # the switch STEP carries shells only
        yield shape
        return
    while ex.More():
        yield ex.Current()
        ex.Next()


def triangles(solid):
    out = []
    ex = TopExp_Explorer(solid, TopAbs_FACE)
    while ex.More():
        face = TopoDS.Face_s(ex.Current()) if hasattr(TopoDS, "Face_s") else TopoDS.Face(ex.Current())
        ex.Next()
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if tri is None:
            continue
        trsf = loc.Transformation()
        pts = np.array(
            [
                [
                    tri.Node(i + 1).Transformed(trsf).X(),
                    tri.Node(i + 1).Transformed(trsf).Y(),
                    tri.Node(i + 1).Transformed(trsf).Z(),
                ]
                for i in range(tri.NbNodes())
            ]
        )
        rev = face.Orientation().name == "TopAbs_REVERSED"
        for i in range(tri.NbTriangles()):
            a, b, c = tri.Triangle(i + 1).Get()
            t = pts[[a - 1, c - 1, b - 1]] if rev else pts[[a - 1, b - 1, c - 1]]
            out.append(t)
    return np.array(out)


def bbox(solid):
    b = Bnd_Box()
    BRepBndLib.Add_s(solid, b)
    return b.CornerMin().Y(), b.CornerMax().Y()


def write_stl(path, tris):
    with open(path, "wb") as f:
        f.write(b"\0" * 80 + struct.pack("<I", len(tris)))
        for t in tris:
            n = np.cross(t[1] - t[0], t[2] - t[0])
            n = n / (np.linalg.norm(n) or 1)
            f.write(struct.pack("<12fH", *n, *t[0], *t[1], *t[2], 0))


def main():
    os.makedirs(OUT, exist_ok=True)
    for key, path in STEP.items():
        groups = {key: []}
        for s in solids(path):
            lo_y, hi_y = bbox(s)
            if key == "receiver" and hi_y < 0.0:
                groups.setdefault("core", []).append(s)
            elif key == "battery" and lo_y >= LEAD_Y - 0.1:
                continue
            else:
                groups[key].append(s)
        for name, ss in groups.items():
            tris = np.concatenate([triangles(s) for s in ss])
            write_stl(os.path.join(OUT, name + ".stl"), tris)
            print(f"{name}: {len(ss)} solids, {len(tris)} triangles")


if __name__ == "__main__":
    main()
