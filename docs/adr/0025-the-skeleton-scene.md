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

## 2026-11-28 the calvaria comes off as a cap (#874)

> Decided on ticket #874 (made while away; Cansin to confirm): the seam's height, its shape, what holds the cap and the
> gap. Each is inferred: no build settles one yet.

The skull's calvaria is its own bone (`calvaria` in `geometry.SKULL`, with its worn copy), so the head's mechanism can
be reached: it lifts straight up off the skull, over the Shields' tops.

- **The cut lives in the skull's Finish** (`export.capped`), not in Python on the exported bones: the review finishes
  each bone in Blender from the scene, and a cut made afterwards would not show there. The cap is a second Finished
  object on a copy of the skull's node group, so both are carved round the mechanism as one bone and differ only in
  which side of the seam is cut away. The committed scene is not re-saved: an older scene's Finish gets the cut at
  export, as it gets its rounding.
- **The seam is level, at z 54 in the head's frame.** The finished skull is open in front under z 50 (the lids' shell
  and the rounding over it); from there up it is one whole ring, 3.7 mm wide at its thinnest and 5.1 at the median.
  z 54 is the lowest seam that leaves twice the print floor of bone over each orbit's opening (4.8 mm at the least). The Shields
  under it top out at z 54.5, so the Cores and the hub are at the opening.
- **Flat, located by Seats.** A flat cut is a teaching skull's, and the cap prints lying on its rim. A flat seam
  alone lets the cap slide until its magnets catch (about half a mm either way), and the hair's crown will sit on
  the cap (Cansin, 2026-11-28, #893), so the cap has to land where it was. It sits on three Seats in the Skin's own
  sizes (`model/skin.py`): a magnet flush in each face, three balls on the skull's face in three V-grooves in the
  cap's, which take the shear. The balls are on the skull so the cap's rim stays flat for the bed. Three full Seats
  over-constrain it, as a Shell's several Seats do; one ball a boss would be the exact coupling and a new layout.
- **The gap is the Seat's, 0.21 mm** (`skin.GAP`): the balls in their grooves hold the two faces that far apart.
  #872's prototype had a 0.4 mm kerf with nothing to hold it open.
- **Each Seat is on a ball boss** of the Seat's radius (7 mm) on the vault's inner side, united with the bone before
  the mechanism is carved, so the carve clears it like any bone. The wall is 4 to 9 mm; a Seat needs 14. The bosses
  stand in front (x 0) and to each side just behind the cap's centre of mass, a mm inside the outer faces, where
  the mechanism leaves 37 mm and more. Straight behind, the nod plate's sweep leaves 8 mm: no Seat there.
- **The seam, the pockets and the grooves are cut from the mesh, exactly** (a mesh boolean after the grid is
  meshed), not from the grid: at a 0.8 mm voxel the grid chamfers every edge, which left a magnet standing 0.7 mm
  proud on its pocket's floor and half the seam's ring bevelled. The exact cut leaves a dozen zero-volume folds a
  piece on the seam's edges; the STL writer drops them, and the pieces are closed.
- **Room for the Skin's Seats in bone** (#850): the crown's face up on the cap's top, 40 mm and more above the
  bosses; the face's top one fits on the forehead's midline either under the seam (its middle at z 47 or lower,
  over the lids' shells) or over it (z 61 or higher), 5 mm clear of the front boss's pocket. They are cut the way the
  cap's own are, when #850 places them.

**Considered:** a conical or stepped seam (it keys the cap, but its rim no longer lies on the bed, and a rabbet
halves a 4 mm wall under the print floor); the magnets standing proud as pins (a voxel's chamfer at the pocket's
mouth is as deep as the pin); a bare flat seam with magnets in 5 mm bosses (the smallest, built first: it slides).

## 2026-11-28 the Skin's Seats in bone (#850)

> Decided on ticket #850 (made while away; Cansin to confirm), with the cap's implementer on #874. Each size is
> inferred: no build settles one yet.

Seven of Morty's Seats are in bone (`model/skin.py` `SEATS`, carriers `skull` and `calvaria`): three for the hair's
crown, facing up on the cap; three for the hair's back, facing back on the occiput; the face's top one, facing
forward on the forehead under the cap's seam.

- **Cut at export, like the cap's own** (`export.seated`): the pocket and three V-grooves from the mesh, exactly, in
  the bare copy and the worn one. `model/skeleton` `job()` passes every Seat whose carrier is a bone.
- **A Seat is a flat cut into the bone**, at the lowest point of the bone's surface under its 14 mm disc and 0.5 mm
  wider all round, so nothing stands proud on the bare skull and the Shell's boss comes down onto it free. The bone
  is curved, so the flat is a notch at its high side: 0.8 to 2.6 mm deep for the crown's, 1.4 to 4.2 mm for the
  back's, 5.1 mm for the face's, on the forehead's slope.
- **Near the midline.** A Seat faces its Shell's way off, so its flat is level for the crown and upright for the
  back. Further out the vault and the occiput fall away under such a flat: at x 25 it cuts 4 mm into a 4 mm wall.
- **The bone is made solid behind each magnet's pocket**: a ball on the Seat's axis, united with the bone before the
  mechanism is carved, like the cap's bosses. It leaves the print floor (2 mm) round the pocket and behind it,
  where the wall alone left 0.1 to 1.5 mm at five of the seven.
- **The crown and the cap hold equally, and that stands.** Three pairs each, 13.7 N. Lifted steadily and upright, the
  crown parts first by the cap's own weight (0.85 N); lifted by one edge it may bring the cap with it. Both lift
  straight up and part by hand, and each lands where it was on its own Seats. Fewer pairs on the crown would let
  it rock (two hold 41 N·mm against about 40 from a 1 g sideways shake); a fourth on the cap has no room at the back.

## 2026-11-28 the chin's Seat and the mandible's hold on its carrier (#850, #968)

> Cansin picked both on #893 (sixth round): the chin Shell's Seat flush in the mandible's front, and the mandible
> held on the jaw's carrier by two magnet pairs. How they are built was decided on #850 (made while away). Each
> size is inferred: no build settles one yet.

- **The mandible's Finish gets an exact cut of its own** (`export.seated`): a mesh boolean after the grid is meshed,
  as the capped skull has for its seam. A bone's cutters are its own collections, so no Finish is cut, or grown,
  by a helper that stands in another bone.
- **The chin's Seat is at (0, −7.8, −81) in the head's frame, facing forward.** It has 14 mm of height for its
  14 mm boss and no more. Over it is the mouth line, the chin's top: at z −78 the boss stood 2.3 mm over it, in
  the face's wall. Under it is the face's own edge under the jaw, which comes up between the bone and the chin's
  wall as the jaw opens wide (to z −88 at the bone's front, 1.2 mm higher each mm forward): at z −82 the boss met
  it. So the flat is 1.3 mm deeper than the lowest of the bone's front, where that edge is lower: a notch 5.2 mm
  deep at its high side, 4 mm of bone behind it. And **the chin's boss gives way to the face's edge**, a seam's
  gap round it over the jaw's range (`shells._clear`): a boss is no skin. One Seat: three balls locate the chin whole, and one pair (4.6 N) holds its
  few grams. **No ball behind its pocket**: the mandible is solid, unlike the skull's shell.
- **The hold is two plain magnet pairs**, each a magnet flush in the front of the carrier's bar and one in the bone
  facing it, face to face (`model/neck.py` `JAW_HOLD`). No balls and no gap: the grooves the Finish cuts for the
  carrier locate the bone, the magnets only hold it. The bone leaves 60° off the pairs' axis, so half of each
  pair's 6.2 N holds it: 6.2 N for the two against 2.5 N (2.3 N as the chin is pulled off its own Seat, and 0.2 N
  of bone and chin), SF 2.5. At 0.1 mm apart it is 2.1 and at `skin.GAP` 1.8, so the bone's magnets are glued in
  against their partners.
- **The pairs are 6 mm either side of the middle, not 8.** At 8 mm the pocket cuts through the ends of the chains'
  last spans where they run into the bar, and leaves edges of 0.02 to 0.25 mm, the kind Linux's OCCT has read as
  an invalid jaw. Out to 6 mm the bar is plain. The bone lies on the bar there on the left and 0.1 to 0.5 mm off
  it on the right, so the right magnet may stand that far proud of its pocket.
- **The bar is thickened behind each pocket**, a 3 mm disc a magnet's depth out of its back: the pocket alone left
  the bar SF 1.5 at the mouth servo's stall, where it twists; with the disc it is 2.5 or more (the plain bar 2.4).

**Considered:** a third pair at the middle (the bar is 0.6 mm off the bone there, right behind the chin's Seat); a
flat on the bar's front for each magnet (its plane lies along the bar's own front line, which left slivers); the
hold as Seats with balls (the bone would then sit on two locations at once).
