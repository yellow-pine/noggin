"""Signed distances to the actual closed reference triangles; no hull, normal-sign or convex approximation.

VTK is already installed by CadQuery. Its C++ locators make dense fitting scans practical; independent ray/winding
checks still adjudicate ambiguous self-intersections in an authored reference. This module never reads/writes assets.
"""

import numpy as np
from vtkmodules.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData
from vtkmodules.vtkFiltersCore import vtkImplicitPolyDataDistance
from vtkmodules.vtkFiltersModeling import vtkSelectEnclosedPoints


class Envelope:
    def __init__(self, vertices, faces):
        vertices, faces = np.asarray(vertices, dtype=float), np.asarray(faces, dtype=np.int64)
        if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
            raise ValueError("An envelope needs finite XYZ surface vertices")
        if faces.ndim != 2 or faces.shape[1] != 3 or not len(faces) or faces.min() < 0 or faces.max() >= len(vertices):
            raise ValueError("An envelope needs valid surface triangles")
        points, cells = vtkPoints(), vtkCellArray()
        points.SetData(numpy_to_vtk(vertices, deep=True))
        cells.SetData(
            numpy_to_vtkIdTypeArray(np.arange(0, 3 * (len(faces) + 1), 3, dtype=np.int64), deep=True),
            numpy_to_vtkIdTypeArray(faces.ravel(), deep=True),
        )
        self.surface = vtkPolyData()
        self.surface.SetPoints(points)
        self.surface.SetPolys(cells)
        if not vtkSelectEnclosedPoints.IsSurfaceClosed(self.surface):
            raise ValueError("The reference envelope must be closed and manifold before classifying containment")
        self.nearest = vtkImplicitPolyDataDistance()
        self.nearest.SetInput(self.surface)
        self.inside = vtkSelectEnclosedPoints()
        self.inside.SetTolerance(1e-8)  # Fraction of reference diagonal; much smaller than a micrometre here.
        self.inside.Initialize(self.surface)

    def distance(self, points):
        """Positive inside, negative outside, in the input mesh's units; actual nearest triangle distance."""
        points = np.asarray(points, dtype=float)
        if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
            raise ValueError("Containment queries need finite XYZ points")
        return np.array(
            [abs(self.nearest.EvaluateFunction(p)) * (1 if self.inside.IsInsideSurface(p) else -1) for p in points]
        )
