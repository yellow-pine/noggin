# The desk eyes on the base plate: why the model clashed (2026-11-01, #172)

The question (#172, from PR #168's review): Cansin's side photo has the servo brackets' feet flat on the plate, but the
model then put our eye bracket's rail 5 mm into the plate and the L servo bracket 1.6 mm into it. #168 first lifted the
eyes 5 mm, then reverted the lift and logged the conflict. The build outranks the model, so this note finds the
model's error.

## The conflict and its two sources

- The build: Cansin's side photo (docs/build-photos/eyes-side.jpg) shows the pink servo brackets standing flat on the black
  plate. The model has always put the feet on the plate top, z 3 (geometry.pt_to_eyes_standalone).
- The model: our eye bracket (model/printed/eye_bracket.py) is the designer's main bracket v2 (03-mouth). Its rail,
  y -40.6..-30.6 in the eyes frame, reaches 5 mm below the feet (y -35.6). The stem sat in the pan bearing recess at
  the PT origin, where the plate's pivot boss (r 4.75, up to z 5) stands 2 mm above the plate top. The L servo bracket's
  stem tab rests on the boss, so it sat 1.6 mm deep. The engine's mesh judge (model/engine/meshes.judge) gave depths of
  2.64 for the eye bracket, 1.59 for the L servo bracket and 0 for the R servo bracket in noggin-eyes,
  noggin-mouth and noggin-stage1 alike. Those three documents use the same frame
  (stages.BASE_IN_EYES = geometry.EYES_ON_BASE), so the eyes-only document has no frame error of its own.

## Findings: two errors, both needed

Each finding below changes one variable on the stage-1 document. Each probe swaps in a part or a frame and checks the
plate against the eye bracket and against both servo brackets.

| eye bracket | stem at | eye bracket depth | L servo bracket depth |
|---|---|---|---|
| v2 (ours) | pan recess (0, 0) | 2.64 | 1.59 |
| v2 (ours) | plate slot (0, -16.5) | 2.58 | 0 |
| v1 (designer STL) | pan recess | 2.27 | 1.59 |
| v1 (designer STL) | plate slot | 0 | 0 |

1. The wrong bracket. The desk build uses the designer's first main bracket, `01-eyes/models/main bracket.stl`, not v2.
   - STL nominals [M]: v1 has a box of x -28..87, y -40.6..4.0, z -4..18. Below y -30.7 it has only the stem
     (x 23.5..35.5), which ends at y -40.6. v2 has a box of y -45.6..8.5. It adds the rail (x -3.42..73.42) and the
     raised band to y 8.5, and its stem is 5 mm longer (docs/research/2026-10-31-model.md, 03-mouth).
   - The photos: in docs/build-photos/eyes-front.jpg and eyes-rest-front.jpg, the servo brackets' plates come down to the
     base plate either side of the stem. No rail crosses in front of them, and no row of rail holes shows. In
     printed-parts.jpg, the v2 bracket (rail and its row of holes) is a separate black print, the neck's.
   - Our servo brackets match their STLs: feet at y -35.6, plate z 18..21 (L/R servo bracket.stl, y -35.6..2.5). The
     base plate matches its STL: plate z -2..3. So no printed part's height is off; the model used the wrong part.
2. The wrong socket. The stem goes through the base plate's front slot, not the pan recess. The slot is a 12 x 5 through
   slot at x -6..6, y -19..-14, the stem's exact section (model/printed/base_plate.py RECTS [M]). The plate is 5 mm
   thick, which is the v1 stem's length below the feet, so the stem fills the slot flush with the underside.
   - The photos: in docs/build-photos/eyes-top.jpg and eyes-rest-top.jpg, the bearing recess (black, round, with its
     pivot hole) shows between the two servo brackets, behind the stem, and the stem does not cover it. In the side
     photo, the eyeballs reach about 33 mm in front of the plate's front edge. The recess placement gives about 20 mm and
     the slot about 36 mm.
   - The model's comment "stem in the pan recess, builder-confirmed" dates from Twin T2 (commit 5c58efb). It put v2 there
     with the stem bottom 1.5 above the plate top [I]. With the boss standing in the recess, no 12 x 5 stem fits there.
     The photos settle it the other way.

## What the model does now

- geometry.DESK (noggin-eyes, noggin-stage1) builds the desk eye bracket (model/printed/eye_bracket.py
  `build(desk=True)`: no rail, no raised band, stem bottom y -40.6). The rail bracket stays where the neck or the mouth
  needs it: stages 2 and 3, and noggin-mouth.
- pt_to_eyes_standalone and EYES_ON_BASE put the stem in the slot: eyes z 15.5 is at PT y -16.5, and the feet are at
  z 3 as before. STEM_AT for stage 1 is (0, -16.5, -2), so the stem bottom is flush with the plate's underside.
- The guard: in model/engine/test_meshes.py, for both desk documents, nothing of the eyes sits inside the plate and both
  servo brackets touch the plate top. model/test_mjcf.py no longer lists the plate against the servo brackets or the
  eye bracket in TOUCH. noggin-mouth carries the rail bracket on the desk base, a pairing never built, so it adds the
  eye bracket to MOUTH_ON_DESK.

## Left open

- The v2 bracket's colour. geometry.PRINTED gives "eye bracket" as Milky Pink, but the v2 print in printed-parts.jpg is
  black. The pink one in the build is the desk bracket. This is not changed here.
