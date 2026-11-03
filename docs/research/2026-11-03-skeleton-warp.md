# Warping real bone meshes into a cartoon bust, headless in Blender (2026-11-03)

The realistic Skeleton starts from real bone meshes (the 3Demon skull and mandible, Printables 777324; a C1/C2 pair;
BodyParts3D 4.0 for the cervical spine, ribcage, sternum, costal cartilages, clavicles and scapula tops, see
`2026-11-03-realistic-skull-models.md` and `2026-11-03-open-skeleton-meshes.md`) and must end up inside a Morty head,
neck and Torso of about 140 W × 120 D × 150 H mm (head). Hard landmarks: each orbit centred on an eyeball, the
mandible's condyles on the jaw hinge axis, the atlas on the tilt axis, the ribcage base on the Torso floor. The bones
clear the mechanism (carved afterwards) and stay printable: walls of at least 2 mm, rounded edges, sutures as soft
grooves. Which deformation method, scripted headless in CI (Blender 5.x, bpy, Python 3.13, numpy/scipy), does this
best?

All sources read on 2026-11-03. Primary sources are the Blender manual's own source files
(`projects.blender.org/blender/blender-manual`, branch `main`, the 5.2 LTS manual), Blender's release notes and
commits, the SciPy 1.18 reference, and the papers each tool cites. Facts checked on the local Blender 5.2.2 LTS with
`bpy` are marked **(checked)**; small throwaway prototypes are marked **(prototype)**; anything else ours is marked
inferred.

## 0. What the environment gives us

- Blender 5.2.2 LTS ships Python 3.13.13 and numpy 2.3.4, and **no scipy** (`import scipy` fails) **(checked)**. The
  repo's model venv (Python 3.14) already has scipy 1.18.1 and trimesh 5.2.0 (`pyproject.toml`). Inferred: run the
  warp maths in the model venv and hand Blender only the warped meshes, rather than pip-installing scipy into
  Blender's Python in CI.
- The skull is dense: 1.96 M faces, 73 MB OBJ, 13 watertight bodies (`2026-11-03-realistic-skull-models.md`). That
  matters for every method with a bind or a solve (below).
- Blender 4.5 added a third Boolean solver, **Manifold**, built on the Manifold library: "much more robust than the
  float solver", "usually as fast as, and sometimes faster than" it, and "it only works when all the arguments are
  manifold -- i.e., each edge is adjacent to exactly two faces" ([4.5 release notes,
  modeling](https://developer.blender.org/docs/release_notes/4.5/modeling/)).
- Blender 5.0 added volume grid sockets and nodes to Geometry Nodes: "Mesh to SDF Grid, Points to SDF Grid, and Mesh
  to Density Grid create grids directly from other geometry types", "Grid to Mesh converts the surface of a grid at a
  specific threshold to a mesh" ([5.0 release notes, geometry
  nodes](https://developer.blender.org/docs/release_notes/5.0/geometry_nodes/)). Blender 5.2 exposes
  `GeometryNodeMeshToSDFGrid`, `GeometryNodeSDFGridOffset`, `GeometryNodeSDFGridBoolean`, `GeometryNodeSDFGridFillet`,
  `GeometryNodeSDFGridMeanCurvature`, `GeometryNodeSDFGridLaplacian`, `GeometryNodeSDFGridMean/Median` and
  `GeometryNodeGridToMesh` **(checked)**. These change the carving answer (§3).

## 1. The seven candidates

### Lattice (free-form deformation)

- The Lattice modifier deforms an object by a Lattice object; options are Object, Vertex Group and Strength
  ([manual, lattice modifier](https://projects.blender.org/blender/blender-manual/src/branch/main/manual/modeling/modifiers/deform/lattice.rst)).
  The lattice has U, V, W point counts and a per-axis interpolation of Linear, Cardinal, Catmull-Rom or B-Spline
  ([manual, lattice](https://projects.blender.org/blender/blender-manual/src/branch/main/manual/animation/lattice.rst));
  at most 64 points per axis **(checked: `Lattice.points_u` hard max 64)**.
- The method is Sederberg and Parry's free-form deformation: a vertex's new position is a fixed, linear blend of the
  control points ([Sederberg and Parry 1986, doi:10.1145/15886.15903](https://doi.org/10.1145/15886.15903)).
- **Landmarks:** poor directly. A B-spline lattice approximates its control points rather than passing through them,
  so a landmark lands where it should only if we solve for the control points (a least-squares fit, since the map is
  linear in them). Inferred: that means re-implementing Blender's lattice evaluation in numpy to get the weights,
  which is fragile.
- **Smoothness:** very good with B-Spline. **Bone-like:** good at coarse resolution, but a coarse lattice cannot
  separate orbit, condyle and atlas targets 10 to 20 mm apart. **Determinism:** fully deterministic, no bind.
  **Effort:** low to set up, high to hit landmarks exactly.

### Mesh Deform (cage, harmonic coordinates)

- "allows an arbitrary mesh (of any closed shape) to act as a deformation cage around another mesh"; "it can be very
  slow to compute the binding"; Precision "can greatly increase the time it takes to complete the binding"; the bind
  "can take a long time ... It is also possible that Blender will run out of memory and crash"; "Significant changes to
  the entire cage mesh ... can cause noticeable artifacts ... a known limitation"; cage normals must point outward;
  smaller inner cages (for example "two small sphere cages ... around [eyes]") add control
  ([manual, mesh deform](https://projects.blender.org/blender/blender-manual/src/branch/main/manual/modeling/modifiers/deform/mesh_deform.rst)).
  Precision runs 2 to 10, default 5 **(checked)**.
- The manual cites harmonic coordinates ([Joshi, Meyer, DeRose, Green, Sanocki 2007,
  doi:10.1145/1276377.1276466](https://doi.org/10.1145/1276377.1276466)): interior-local, smooth weights.
- **Landmarks:** indirect. Cage vertices are not on the bone, so a landmark hits its target only after iterating the
  cage. **Smoothness:** good. **Bone-like:** good for moderate change, artefacts for the large non-uniform change a
  cartoon head needs (manual warning above). **Determinism:** deterministic once bound, but the bind on a 2 M-face
  skull is the cost and the memory risk the manual warns of; it needs the operator
  `bpy.ops.object.meshdeform_bind` under a context override. **Effort:** high (an authored cage is a second model to
  maintain).

### Surface Deform

- Transfers a target surface's deformation to another mesh; the target must have no edge with more than two faces, no
  concave faces, no doubles, no faces with collinear edges; Interpolation Falloff sets smoothness; "The further a mesh
  deviates from the target mesh surface, the more likely it is to get undesirable artifacts"
  ([manual, surface deform](https://projects.blender.org/blender/blender-manual/src/branch/main/manual/modeling/modifiers/deform/surface_deform.rst)).
  Falloff runs 2 to 16, default 4 **(checked)**.
- Inferred: the natural target would be the Shells, which sit 5 to 20 mm away from the bone, exactly the case the
  manual warns about, and the Shells' topology is not a morph of a real head anyway. It is a proxy-cloth tool, not a
  shape-matching tool. **Rejected.**

### Laplacian Deform with anchors

- Poses a mesh "while preserving geometric details" with differential coordinates; anchors in a vertex group, the rest
  solved; Repeat iterates the rotation of the differential coordinates; "If the mesh is dense, with a number of
  vertices greater than 100,000, then it is possible that the nonlinear optimization system will fail"; errors if
  vertex or edge counts change after bind ([manual, laplacian
  deform](https://projects.blender.org/blender/blender-manual/src/branch/main/manual/modeling/modifiers/deform/laplacian_deform.rst)),
  after [Sorkine et al. 2004, Laplacian surface editing, doi:10.1145/1057432.1057456](https://doi.org/10.1145/1057432.1057456).
- **Landmarks:** exact for anchored vertices. **Bone-like:** the best of the set at keeping local detail (foramina,
  ridges) under a large move. **Smoothness:** good away from anchors; anchor patches can crease. **Determinism:** a
  linear solve, deterministic for a given input, but the 2 M-face skull is 20 times past the manual's 100 k warning, so
  it needs a decimated copy, and the bind is an operator (`bpy.ops.object.laplaciandeform_bind`). **Effort:**
  medium. Inferred: it is a surface method, so it does not move other bones consistently (the mandible and C1 would
  each need their own anchors placed to match the skull's result).

### Landmark RBF / thin-plate-spline warp (scipy `RBFInterpolator`)

- `RBFInterpolator(y, d, neighbors=None, smoothing=0.0, kernel='thin_plate_spline', epsilon=None, degree=None)`;
  thin-plate spline is the default kernel (`r**2 * log(r)`) with a minimum polynomial degree of 1 (so the affine part
  is exact); with `smoothing=0` "the interpolant perfectly fits the data"; uniquely solvable if the landmarks are
  distinct and not all coplanar ([SciPy 1.18 reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.RBFInterpolator.html)).
  RBFs "should be used with caution for extrapolation outside of the observed data range" ([SciPy tutorial,
  scattered data](https://docs.scipy.org/doc/scipy/tutorial/interpolate/ND_unstructured.html)).
- The thin-plate spline is the interpolant of least bending energy through the landmarks, and splits into an affine
  part plus "principal warps" ([Bookstein 1989, doi:10.1109/34.24792](https://doi.org/10.1109/34.24792)): the
  standard landmark warp in morphometrics, which is the same job (one anatomy onto another by homologous points).
- **(prototype)** 60 landmarks, 2 M points, scipy 1.18.1 in the model venv: fit plus evaluation 0.53 s, landmark error
  4e-12 mm, two runs bit-identical. With an anisotropic scale plus 4 mm of noise on the targets, the Jacobian
  determinant over the volume ranged 0.32 to 1.87: the warp stayed fold-free but locally compressed volume to a
  third, which thins walls by the same order. A real check, not a hypothetical.
- **Landmarks:** exact. **Smoothness:** the smoothest possible by construction. **Bone-like:** good where landmarks
  are well spread, poor where they crowd or conflict (local squash, possible fold: a determinant of 0 or below). One
  field moves every bone consistently, so the skull, mandible and C1 keep their joints. **Determinism:** a dense
  LAPACK solve on tens of points, then one matrix product per vertex. **Effort:** low (a few lines of numpy around
  scipy), plus landmark picking.

### Geometry Nodes

- Inferred: Geometry Nodes has no linear-solve node, so it cannot fit a TPS or a Laplacian system itself; it could
  only apply precomputed displacements. As a warp tool it adds nothing over the TPS above.
- As a **finishing** tool it is now the strongest option (§3): Mesh to SDF Grid, SDF Grid Offset ("useful for adjusting
  wall thickness"), SDF Grid Boolean ("Useful for cutting holes or carving one SDF out of another"), SDF Fillet
  ("smooths or rounds off concave internal corners ... useful for ... removing hard transitions after boolean
  operations"), SDF Grid Mean Curvature, and Grid to Mesh
  ([manual, volume operations](https://projects.blender.org/blender/blender-manual/src/branch/main/manual/modeling/geometry_nodes/volume/operations),
  [Mesh to SDF Grid](https://projects.blender.org/blender/blender-manual/src/branch/main/manual/modeling/geometry_nodes/mesh/operations/mesh_to_sdf_grid.rst)).

### Per-bone affine pose plus a global warp

- Each bone gets its own similarity or affine transform fitted to its landmarks (a least-squares fit; scipy's
  `Rotation.align_vectors` already serves `model/gimbal.py`), then a gentle global TPS removes the residual.
- **Bone-like:** best. A vertebra, rib or clavicle under a similarity transform is still exactly that bone; an affine
  keeps straight lines straight. **Landmarks:** exact after the TPS stage. **Determinism:** deterministic. **Effort:**
  low. Inferred: the skull cannot be done this way alone, because the cartoon look is a regional change inside one bone
  (cranium up, face and jaw down, orbits opened), which only a non-affine field gives.

### Scorecard (inferred from the above)

| Method | Landmarks | Smooth | Bone-like | CI determinism | Effort |
|---|---|---|---|---|---|
| Lattice | approximate unless solved | high | fair (coarse) | high | low, high to be exact |
| Mesh Deform | indirect | good | fair under large change | bind slow, memory risk | high (cage) |
| Surface Deform | indirect | fair | poor at distance | ok | medium; wrong tool |
| Laplacian Deform | exact (anchors) | good | best for local detail | needs under 100 k verts | medium |
| TPS (scipy) | exact | best | good if landmarks spread | high | low |
| Geometry Nodes | n/a (no solver) | n/a | n/a | high | n/a for warp; best for finishing |
| Per-bone affine + TPS | exact | high | best overall | high | low |

## 2. Animatus as an artistic reference

- Hyungkoo Lee's *Animatus* series (from 2005; shown at Arario Gallery 2 September to 8 October 2006) set out "to
  analyze anatomical structures and physical forms of animation characters" and "to visualize the possible anatomical
  foundation" of them ([Arario Gallery](https://www.arariogallery.com/exhibitions/91-lee-hyungkoo-animatus)). Lee made
  "detailed drawings" of "bone structures based on animal anatomy", worked out "how giant cartoon eyeballs might
  actually function", and his earlier *Homo Animatus* is "a runty, big-skulled creature" ([Ben Davis, The Village
  Voice, 18 March 2008](https://www.villagevoice.com/mickeys-fibula-courtesy-of-hyungkoo-lee/)). His works "often
  begin with ironic reproductions of animal skeletons, X-rays, and anatomical busts", in resin, glass and oil paint
  ([Generazione Critica, 2025](https://www.generazionecritica.it/en/works-in-focus/canis-d-animatus-muscle-attachment-hyungkoo-lee/)).
- No primary source found gives his proportions per region; the artist interview on Ocula returned 403. Inferred
  from the sources above and the target head (`2026-11-03-cartoon-head-proportions.md`): keep real bone *detail* and
  move only the *proportions*: the neurocranium (vault, occiput) scales up, the orbits grow to hold the eyeballs, the
  viscerocranium (maxilla, nasal, zygomatic) and the mandible scale down, the neck stays thin. That is exactly a
  landmark warp with the cranium landmarks pushed out and the face landmarks pulled in, so the reference supports the
  TPS choice rather than a uniform scale.

## 3. Carving and remeshing warped meshes

- Boolean modifier: "Only Manifold meshes are guaranteed to give proper results"; the Manifold solver "will not work
  at all on non-manifold meshes"; Exact "offers the best results and has full support for overlapping geometry, but is
  much slower", with Self Intersection and Hole Tolerant options that cost more time; Float lacks overlap support
  ([manual, boolean modifier](https://projects.blender.org/blender/blender-manual/src/branch/main/manual/modeling/modifiers/generate/booleans.rst)).
- The Exact solver "is not guaranteed to work if the operands are not volume-enclosing (technically: PWN -
  piecewise constant winding number)" ([Howard Trickey, commit 6f63417b, 7 February
  2021](https://archive.blender.org/lists/bf-blender-cvs/2021-February/153093.html)); PWN comes from [Zhou, Grinspun,
  Zorin, Jacobson 2016, Mesh Arrangements for Solid Geometry](https://www.cs.columbia.edu/cg/mesh-arrangements).
  Inferred: a warp that folds (determinant at or below 0) or pushes two bones into each other produces exactly the
  self-intersecting, non-PWN input that breaks Exact and that Manifold rejects outright; on a 2 M-face skull Exact is
  also very slow.
- Voxel remesh "has no inner (self-intersecting) geometry" and suits "cleaning up a mesh for sculpting or 3D
  printing" ([manual, retopology](https://projects.blender.org/blender/blender-manual/src/branch/main/manual/modeling/meshes/retopology.rst));
  "The input mesh should have some thickness" ([manual, remesh
  modifier](https://projects.blender.org/blender/blender-manual/src/branch/main/manual/modeling/modifiers/generate/remesh.rst)).
  Inferred: a voxel step before any boolean is what turns a warped, possibly self-touching mesh into a valid solid.
- The SDF grid nodes do the remesh, the thickening, the carve and the rounding in one field, with no mesh boolean at
  all. **(prototype)** in headless Blender 5.2.2: icosphere r 20 mm → Mesh to SDF Grid (0.25 mm voxels, band 12) →
  minus (a 20 mm cube → Mesh to SDF Grid → SDF Grid Offset +2 mm clearance) → SDF Fillet 5 iterations → Grid to Mesh:
  131 k vertices, **0 non-manifold edges**, positive signed volume (outward normals), 1.7 s, the same vertex hash on two
  evaluations. Gotcha: Grid to Mesh's Threshold defaults to **0.1** (a density value); for an SDF it must be set to 0,
  or the output is empty.
- Wall thickness: offsetting an SDF outward by *a* then inward by *b* makes every surviving wall at least 2(*a* − *b*)
  thick and closes gaps narrower than about 2*a* (inferred from the offset definition). So +1.25 mm then −0.25 mm gives
  the 2 mm floor with 1 mm of net growth, which the landmark targets must allow for. It also fills real sutures, so
  sutures are re-cut afterwards as soft grooves (below). Check the result with
  `trimesh.proximity.thickness(mesh, points, method='max_sphere')` (trimesh 5.2.0, in the venv) as an assert-based
  gate.

## 4. Recommendation

**Per-bone similarity pose plus a landmark thin-plate-spline warp (scipy, in the model venv), then a Geometry Nodes
SDF finish in Blender (thicken, carve the mechanism with clearance, fillet, re-cut sutures, mesh).** The TPS is the
only candidate that hits every hard landmark exactly, is smooth by construction, moves the skull, mandible and atlas
by one consistent field, and is a plain deterministic linear solve. The SDF finish makes printability and the carve
robust regardless of what the warp did to the topology, so Exact and Manifold booleans are not on the critical path.
Laplacian Deform is the fallback for a local touch-up on a decimated bone if the TPS flattens a detail; Lattice, Mesh
Deform and Surface Deform are not worth their cost here.

### Pipeline sketch

1. **Prepare (venv, trimesh):** load each source bone in millimetres, merge the skull's 13 bodies per bone, decimate to
   a working density (inferred: about 200 k faces for the skull is plenty at 0.25 mm voxels).
2. **Landmarks (a checked-in table):** per bone, source points picked once (orbital rim ring of about 8 points per
   side, condyle centres, foramen magnum and occipital condyles, C1 facets, C2 dens, sternum ends, rib 10 to 12 lowest
   points, clavicle ends, acromion) and their targets derived from the model (eyeball centre plus rim radius,
   hinge-axis endpoints, tilt axis, Torso floor), never typed twice (ADR 0011). Add a sparse frame of "stay" points
   around the bust so the TPS never extrapolates.
3. **Per-bone pose:** fit a similarity transform per bone to its landmarks (vertebrae, ribs, clavicles, scapulae,
   mandible); apply.
4. **Global warp:** fit `RBFInterpolator(src, dst - src, kernel='thin_plate_spline')` on all landmarks, apply to every
   vertex of every bone. Assert: landmark error under 0.1 mm, Jacobian determinant over 0.5 everywhere on a sample
   (no folds, no extreme squash), every bone inside its Shell's inner envelope.
5. **Finish (Blender, Geometry Nodes, headless):** per bone or bone group, Mesh to SDF Grid (0.25 mm) → Offset +1.25
   → Offset −0.25 → SDF Grid Boolean difference with the mechanism's SDF offset by the clearance → SDF Grid
   Boolean difference with capsules along the warped suture curves (about 0.6 mm radius) → SDF Fillet → Grid to Mesh
   (Threshold 0) → evaluated mesh to STL/GLB.
6. **Gates (venv):** watertight and manifold, min thickness 2 mm by `trimesh.proximity.thickness`, clearance to the
   mechanism, landmark positions within tolerance after the 1 mm growth. Compare by tolerance, not by file hash.
7. **Where it runs:** CI on the default branch, with the other heavy builds (CONTRIBUTING.md, #696); agents run only
   steps 1 to 4 locally on decimated meshes.

### Risks

1. **Thin bone.** At roughly 1:1 scale the real orbital walls, ethmoid, conchae and pterygoid plates are already under
   2 mm, and shrinking the face thins them further (the prototype saw local volume down to a third). The 2 mm floor
   then comes only from the SDF growth, which softens detail and moves surfaces by about 1 mm; the landmark targets
   must build that in.
2. **Folds and extrapolation.** A TPS gives no guarantee against folding when landmarks crowd or conflict (orbit ring
   versus condyles in a 150 mm head), and it extrapolates unreliably outside the landmark hull. Needs the frame points
   and a Jacobian-determinant gate, or the carve gets non-solid input.
3. **Cost and reproducibility in CI.** The 2 M-face skull at 0.25 mm voxels is memory- and time-heavy, and
   bit-identical output across machines is not guaranteed (threaded BLAS, OpenVDB); gate on geometric tolerances and
   keep it on the default branch's heavy run.

Also note: the 3Demon skull is CC BY-SA, so its warped files stay CC BY-SA 4.0
(`2026-11-03-open-skeleton-meshes.md` §0); the licence check comes before adoption.
