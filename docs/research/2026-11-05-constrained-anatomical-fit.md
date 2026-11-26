# Constrained anatomical fitting

Checked 2026-11-05 against installed SciPy1.18.1, NumPy2.5.4 and VTK9.6.2. These dependencies are already locked;
VTK is supplied by CadQuery. The geometric budgets and private-input policy come from the confirmed #893/#979
decisions, not these libraries. No optimizer result alone certifies anatomical feasibility.

- SciPy supports bounded nonlinear equality and inequality constraints. `trust-constr` supplies general nonlinear
  constraints; SLSQP accepts vector inequality functions and their Jacobians. A fixed constraint vector is solved
  before adding held-out violations and restarting. [SciPy minimization interface](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html),
  [NonlinearConstraint](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.NonlinearConstraint.html).
- Independent singular values measure principal local length factors. Apply the declared **regional uniform**
  scale before checking them; fitting a separate per-Bone similarity afterward would hide deformation. Final
  triangle tangents must also include Sculpt edits. [NumPy SVD](https://numpy.org/doc/stable/reference/generated/numpy.linalg.svd.html).
- VTK's enclosed-point selector classifies a closed, manifold triangle surface using ray intersections. It exposes
  surface-closure checking and a reusable initialized locator. It is not a convex hull or nearest-normal sign.
  Self-intersecting authored surfaces still need independent ray/winding adjudication.
  [VTK9.6 enclosed points](https://vtk.org/doc/nightly/release/9.6/html/classvtkSelectEnclosedPoints.html).
- `vtkImplicitPolyDataDistance` supplies nearest-surface distances. This project's adapter takes their absolute
  values and obtains the sign separately from enclosure, preserving real concave air grooves despite inconsistent
  source normals. [VTK distance class](https://vtk.org/doc/nightly/html/classvtkImplicitPolyDataDistance.html).

Implementation choice: a small, shared Gaussian residual with analytic derivatives, conditioned to vanish at
hard functional anchors. Its serialized coefficients and conditioning data define the same saved/interactive
mapping. This is a bounded parameterization experiment, not a global infeasibility proof. A failed affine or
nonlinear solve means only that no feasible candidate was found in that parameterization and iteration budget.

Actual original C1/occipital and temporal/mandibular opposing-surface witnesses distinguish anatomical articulation
from canal-centroid or bounding-box proxies. Their transformed positions, original/fitted gap relationships,
containment, final surfaces and wiring corridor require separate evidence before adopting a source scene.
