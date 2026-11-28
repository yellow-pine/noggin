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
condyles 3 mm under the tilt axis, the skull's box on the compact head's (`base.DOME`, gone since #1089).
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
  his neck's skin. On #1055's straight canal (C7's foot at y 72, where it was 91.6) the vertebrae already stand 7.2 mm
  under his skin at rest, so that field moves nothing (local lengths 0.999 to 1.0).
- BodyParts3D's decimated meshes hold slivers a smooth field folds; `slivers.py` turned their long edges once, moving
  no vertex. The Warp refuses a fold, a shear past 2.1 or a Jacobian under 0.5 at the eyes and nose (#991), read
  outside the lids' shell alone. The shear limit is Cansin's (2026-11-27, #893): 2.1, where the box fit's was 1.8
  and this fit measures 2.05 (2.27 before the eyes moved onto the Sculpt's). A fit that cannot hold 2.1 stops and
  goes back to him; the limit is not raised to pass it.
- The orbits sit on the Sculpt's own eyeballs' centres (#967's fit, 73.3 mm apart), which are the Mech's eyes
  (`gimbal.EYE`) since #1035. #967's re-laid lids stow in a shell of radius 38 mm round each and their drives leave it
  through a belt behind each eye: both are openings of the skull's Finish before those parts exist.
- The skull's Finish seals its 21 bones into one before it shells and carves: their SDF grown 1.5 mm, then eroded by
  as much (`skeleton.SEAL`), which closes every gap under 3 mm. BodyParts3D's bones only abut, and with the lids'
  shell and the belts open the palate hangs on one junction: the R maxilla's back against the sphenoid's pterygoid
  process, 1.4 mm apart, in the 3.4 mm between the gimbal frame's plate and the tie-bar's sweep. Whether the Finish
  joins them unsealed turns on where the two land on its grid: on the fit before the eyes moved onto the Sculpt's
  (#1035) the palate came off as a second piece (5.3 cm3); on this one it holds unsealed too, on a neck of 17 mm2.
  Sealed, it held on both: a neck of 22 mm2 then, 29.5 now (about 10 mm wide and 3.4 tall). So the seal is what keeps
  the palate from hanging on that chance, and `test_skeleton.py`'s one-piece check holds it only on a fit where the
  two bones miss. The L side has no bridge while today's lower lids sweep the L maxilla away under the plate.
- The skull's Finish first thickens the vault's bones (the fit's `VAULT`: the growth zone's six and the frontal) inward,
  toward the cranium's middle, to at least 2.4 mm (`skeleton.THICK`: the 2 mm print floor and half the voxel), their
  outer side staying where it is. Stretched over Morty's wide head the parietal bones are 0.8 to 2.2 mm thick at the
  temples; the rounding took what was under the floor away and left two holes there (the R about 19 x 10 mm).
  Cansin, 2026-11-27 (#893's second round): close them with bone at the print minimum.
- The gates read the Sculpt (`model/morty`, ADR 0027): `test_skeleton.py` holds each finished bone 2.1 mm under it
  and to no box. The mechanism's gates read it too since #1089 (`model/review`'s `test_hidden.py`, `test_nape.py`
  and `test_head.py`), so `base.DOME`, `base.EYES_UP` and `gimbal.HEAD_MM` are gone.

## 2026-11-28 C5 and C6 slimmed for the neck's skin (#874)

> Decided by Cansin on 2026-11-27 (#893's third round): C5 and C6 are slimmed where the rim of the neck's skin swings
> through them, beyond the usual length budget, in a declared zone for those two vertebrae only. The rule and its
> numbers below were decided on ticket #874 (made while away; Cansin to confirm).

The neck's skin rides the head and ends at the collar (ADR 0030), so its rim swings through the still neck as the head
nods. The vertebrae are fitted under that skin as the still neck sees it: `envelope.turning` reads, at each point,
the least depth under his skin above the collar over the head's tilt (every 1°) and pan (every 2.5°) together, and
under the still skin at rest.

- **The zones are on the original anatomy** (`budget.SLIMMED`), about each vertebra's own canal in plan: C6 all round
  it; C5 from its canal back and beside it, less and less of it round to the front, none straight ahead. Cansin named
  C5's rear arch and C6's body. Measured, C6 stands in both swings (its spine's tip 12 mm out of the nape's skin at
  tilt −20°, its body's lower front 4 to 5 mm into the throat's rim at tilt +20°), so its zone is its whole ring; the
  coordinator confirmed it on #874 as still those two vertebrae only.
- **The rule is explicit, not the field's** (`budget.slim`): the bone is drawn in radially toward its canal's middle
  from 8 mm out, each length beyond that taken to one factor a vertebra, eased in over 2 mm. The fit takes the greatest
  factor of a fixed list (`fit.SLIMS`) that brings the vertebra 2.5 mm under the skin; it finds nothing else. Left to
  the smooth field alone (a 5 mm lattice, floor 0.2), the same room was reached only by dragging C7's spine 19 mm up
  beside them and took ten minutes; coarser lattices did not reach it.
- **The factors: C6 0.4, C5 0.05.** Behind C5's canal the nape's rim leaves 12 mm from the canal's middle at z −118,
  so C5's arch is a plate about 4 mm thick behind its canal: its spinous process is gone in effect. C6 keeps its
  shape at 0.4 of its depth beyond the canal's wall. The floor declared for a slimmed zone is 0.03 (`budget.SLIM`);
  the least length factor used is 0.04 (C5, where the zone's easing by direction shears it) and 0.37 (C6). 1,495 of
  C5's vertices and 1,461 of C6's lie in a zone; 1,394 and 1,431 are squashed past 0.75. The stretch cap stays 1.25
  everywhere (1.18 reached), and every other vertebra keeps 0.75 (0.87 reached).
- **The canals stay open**: nothing within 8 mm of a canal's middle moves, and the canal pins hold (0.0 mm).
- C4's spine and C7's body, 0.6 and 1.0 mm short of the margin, come under it in the neck's field, inside the usual
  budget.
- `model/review/test_nape.py` holds each finished vertebra 2.1 mm under the head's skin at every tilt and pan
  together; before, C5's arch stood 6 mm and more out of the nape's skin tilted back.

**Considered:** trimming the two vertebrae in the Finish (a fifth of C5 and a seventh of C6 gone, no vertebra left to
read: #874's table of 2026-11-27); bending C5's spine up over the rim's arc (it meets C4's, and the whole column of
spines would have to close up to its floor); a factor that changes with height (the bone shears across the step).
