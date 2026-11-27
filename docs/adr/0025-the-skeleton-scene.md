# The realistic Skeleton is a Blender scene

> Decided with Cansin on 2026-11-03/04, spec #893 (its grilling on #872), ticket #873. Amends ADR 0009, 0019, 0020 and
> 0023.
> Amended 2026-11-27 (#850, ADR 0027): the Morty sculpt is committed and public (`model/morty`), so the coarse hull
> below is not needed; the skull's limit is the sculpt's surface less 2.1 mm, not the compact head's box.

The realistic Skeleton's bones are authored by hand, landmark by landmark, until Cansin has no more edits, and Cansin
audits them by turning them in Blender, not in code or pictures. So their source is one committed Blender scene,
`model/skeleton/skeleton.blend` (the Skeleton scene, GLOSSARY), not a Python module: its bones, each with a Warp shape
key (model/skeleton/fit.py's regional fit from the Basis and the Landmarks; Blender only exports the Basis and
applies the Warp, rewarp.py) and a Sculpt key over it for hand edits, and a Finish per exported bone (a live Geometry Nodes SDF stack:
the cranium shelled, the mechanism carved round with clearance, crumbs dropped, meshed). CI fits it to the Mech it just
built: Blender opens the scene, deletes its Scene Mech, puts the Stage 3 document's parts where each bone sees them
(at rest and over every horn's range), runs every Finish and exports each bone (model/skeleton `finish()`, part of `just
ours`), which the pictures, the Viewer and the print files then draw. #873 moved the 3Demon skull and the atlas and axis
in unchanged and removed `model/printed/skull.py`; the bones themselves change from #874.

- **ADR 0009, sources only:** the scene is a source, binary and compressed, under a size cap (a test, no LFS). Its Scene
  Mech is the one derived copy the repo holds: a light, decimated copy of the Stage 3 Mech, so the scene opens fitted,
  which CI replaces on every run and never publishes. The numbers the gates share with the Finish (its voxel, clearance,
  wall) stay in `model/skeleton` and are set on the Finish at export.
- **ADR 0019 (and 0024):** nothing changes in what is published: the exported bones, their pictures and GLB, as before.
- **ADR 0020:** the realistic Skeleton's bones stay visual only; physics runs on the mechanical documents.
- **ADR 0023:** from #874 the bones are one source, BodyParts3D 4.0 (treated as CC BY-SA 2.1 JP, its own LICENSE.md),
  warped into Morty at the unchanged reference scale and eye centres, in place of 3Demon and the atlas-axis. The real
  Morty sculpt is a fit reference kept local only (`docs/references`), never committed or published; a coarse hull of
  our own (low-poly, no sculpt detail) may be committed, so CI can check the bones lie inside him (Cansin, 2026-11-04).

## Considered Options

- Keep the bones in Python (skull.py's voxel carve): reviewable as text, but Cansin can't edit or audit a fit that lives
  in code, and every hand edit would have to be translated into numbers.
- Commit the finished bones: no Blender in CI, but they would go stale the moment the Mech moved, and they are an
  output (ADR 0009).
- Git LFS for the scene: past the free tier's bandwidth for a public repo's clones; a compressed scene under a cap
  instead.

## 2026-11-04 fit amendment

Cansin confirmed the inner Skin as the primary cranial envelope (#893/#874), superseding the original adult-cranium
±10% cap wherever it prevents that fit. Preserve anatomical features, walls and mechanical clearances. The connected
skull, all seven cervicals and upper chest use one original anatomical frame and one shared field; the true central
spinal canal, not a projected lateral foramen, registers the skull base through T1. Regional outer-surface gaps and
signed containment are separate evidence; neither pose-empty coordinates nor a good landmark residual proves fit.

The initial regional working budgets reserve 1.6 mm Skin wall plus 1.6 mm clearance. Raw-vault targets add the finish's
growth reserve. Crown, temple, back and forehead vault regions aim for outer-reference median gaps at most 4.8 mm
and p90 at most 6.4 mm. Natural openings and unavoidable functional keep-outs are named with their evidence; budgets
are not retuned to accept a result. The warp rejects a least Jacobian at or below 0.1 or a landmark miss over 1 mm.
Numerical jobs run on GX10; the private Morph mesh and semantic profiles remain on the Mac.

## 2026-11-05 anatomy and compute amendments

Cansin's confirmed decisions on #893 supersede the preceding maximum-fill targets and Mac-only compute restriction.
Anatomy takes priority over filling unused Skin space. Crown, forehead and vault-fill targets are soft objectives;
actual Skin containment, walls, functional eye/orbit registration, true articular joints, canal continuity and the
hardware wiring corridor remain hard requirements. The old inferred T1/shoulder height and the C1 canal centroid
are not anatomical joint datums: C0 and TMJ registration uses corresponding original articular surfaces. A color
boundary or a mesh's box cannot establish the shoulder girdle's position.

Start from original BodyParts3D Basis coordinates. Report each declared anatomical region's uniform resize and
rigid placement, then enforce local length factors of 0.75–1.25, including the final Sculpt residual. Fixed,
source-stamped posterior/inferior cranial masks and rib/cartilage masks alone may increase their upper bound
smoothly to 1.50, while protecting face, orbit, jaw, C0 and attachment regions. Other bones retain 1.25. No per-Bone
normalization, inherited anisotropic baseline, vertex clamp or automatic budget increase can establish acceptance.
One anatomical frame and joint continuity permit smooth regional fields; they do not require one global TPS.
Saved and interactive rewarps must evaluate the same field and metadata. Optimizer success, positive Jacobians
at sampled points and small landmark residuals each remain insufficient without independent actual geometry checks.

The confirmed reference restores the original arms/body above one horizontal functional base, provisionally the
current CAD floor at world Z=0. Old arm-cut width and whole arm span cannot serve as ribcavity dimensions. The body,
neck, shoulders and arms stay fixed, with head, jaw and eyes moving on their own actual carriers. Original visible
eye geometry stays intact; spherical guides do not replace it.

Under #979, the canonical authored private reference stays on the Mac, while immutable, hash-versioned copies and
dense fitting data may travel by SSH to the trusted GX10 private ignored cache. They remain excluded from git,
public CI, published artifacts and public source scenes. GX10 supplies normal heavy numerical/Blender compute;
the Mac remains the review viewer with its existing resource limit and backup-preserving atomic publication.

## 2026-11-26 adoption (#874)

The scene's bones are BodyParts3D's: the skull's 21 bones (read whole by the skull's Finishes), the mandible and C1
to C7 (`atlas`, `axis`, `c3` to `c7`), each with the #872 prototype's Basis. The Warp resizes each region uniformly
(skull 1.05, mandible 0.95, neck to the canal's height) and gives the skull and the mandible one cubic B-spline
field each, solved against #975's mechanism: the orbits on the eyes, the condyles on the jaw's hinge, the occipital
condyles 3 mm under the tilt axis, the skull's box on the compact head's (`base.DOME`, which the head gate uses).
Every vertex's local length factors stay within this budget's bounds (fit.py raises otherwise) and every functional
landmark within 1 mm. The vertebrae are resized and moved only, each canal on the cervical canal's path. The
prototype's numerical machinery (#976's adapters, constrained Gaussian field, refinement, GX10 exchange) is not
adopted.

The brow stands half an eye cap's radius ahead of the eye centres (`gimbal.CAP_R / 2`), no longer ahead of the caps'
fronts (Cansin, 2026-11-27, #874; model/skeleton/test_skeleton.py holds it). A design change, not a loosened gate:
within the length budget an anatomical brow reaches about 24 mm ahead of the orbits, and Morty's 40.4 mm eyes stand
proud of it. Anatomy comes first.


## 2026-11-27 refit inside Morty's skin (#874)

Cansin's directive on #893 (2026-11-27) makes the Sculpt's surface the bones' limit: every bone stays at least 2.1 mm
under it (the Skin's 1.6 mm wall, grown inward, and 0.5 mm of clearance), where the compact head's box had been.
Measured first (#874): the box-fitted skull stood 10.9 mm out of Morty's forehead, its chin 4.6 and C7's spine 8.6,
with 32 mm unused under his crown, which stands 36 mm over the box's top.

- `model/skeleton/envelope.py` reads the Sculpt as a depth under its outer surface (sheets it holds inside itself, its
  hair's under side, are no skin). The Warp keeps every vertex and every face 2.5 mm under it: the limit and half the
  Finish's voxel, which its remesh can grow a bone by.
- The regions are about life-size: the skull 1.05 (its back and crown then stand at Morty's own), the mandible 1.0
  (0.95 in the box), the neck 0.968 as before. Each takes one field. In the solve the length budget is the hardest
  term, then the skin and the landmarks, last the fill.
- The cranium's outer side is drawn out toward the skin, softly, within the budget: the vault then stands outside the
  mechanism's sweep by its wall and clearance, so the Finish closes it, and the growth zone's under side comes down
  toward his nape (#991's skull-base guides), 1.6 mm clear of the vertebrae over the tilt's and the pan's ranges.
- The neck's vertebrae take a field of their own: each canal and each body's front pinned, the spines bent in under
  his neck's skin.
- BodyParts3D's decimated meshes hold slivers a smooth field folds; `slivers.py` turned their long edges once, moving
  no vertex. The Warp refuses a fold, a shear past 2.2 or a Jacobian under 0.5 at the eyes and nose (#991).
- The orbits sit on the Sculpt's own eyeballs' centres (`skeleton.EYES`, #967's fit, 73.3 mm apart), where the
  Mech's eyes move to. #967's re-laid lids stow in a shell of radius 38 mm round each and their drives leave it
  through a belt behind each eye: both are openings of the skull's Finish before those parts exist.
- The gates read the Sculpt (`model/morty`, ADR 0027): `test_skeleton.py` holds each finished bone 2.1 mm under it
  and to no box. `base.DOME` stays the mechanism's box until its gates read the Sculpt too.
