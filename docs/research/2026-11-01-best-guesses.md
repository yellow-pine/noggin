# Best guesses for the values that waited for a calliper (2026-11-01, #170)

Cansin, 2026-11-01: "assume with best guess, I cannot measure". Every value below is settled by a documented guess and
marked inferred where it is used; none waits for a measurement. Evidence order: the real build's behaviour and photos
(the Mech runs every gesture and its calibrated servo ends, eyes/calibration.json, without binding), then the STEP and
STL nominals. Method: `make sim`'s pose measure (model/engine/run.py `measure`) at each calibrated end, one variable
changed at a time, and the penetrating vertices' extents to see which way each collision runs.

## The lid crank at the closed ends (L -41, R -40)

- Symptom: the crank's plain end 1.0 mm into the eye bracket's outer edge from horn -32. Its inside vertices span
  x -27.94..-27.0 only: a plane overlap along the screw, not a swing into the edge.
- Cause: the model stacks the crank flat on the straight bar (x -27..-30); the bracket edge is x -27..-28. The bar and
  crank turn on the M2 screw under a nut that is not clamped (the joint must turn), so nothing holds the crank on the
  bar: where the edge meets it, it is pushed out along the screw.
- Guess: the crank rides 1.2 mm out (geometry.CRANK_PLAY_MM): 0.2 mm clear of the edge (1.1 is the least that clears),
  its stepped end 1.2 mm off the upper lid's ear on the lid pin. The closed ends run clean; the free travel on that side
  now ends where the straight bar meets the bracket face (y -2.5) from -50, so the lid limit is servo 41..129 (horn
  -49..+39, geometry.LIMITS).

## The eye horns' tooth (L eye -32)

- Symptom: the L eye horn 0.18 / 0.44 mm into the servo bracket and eye bracket at horn -32 (clean at -30, not at -31).
- The program centres each eye at the mean of its calibrated ends, servo 88 (eyes/eyes.py `_eye_angle`), and the
  rest-front photo (docs/build-photos/eyes-rest-front.jpg) has both pupils straight ahead there; the rest-top reading
  less its camera tilt gave +3.2 each (docs/research/2026-10-31-shafts.md). The model's neutral (eyes straight, the STL
  pose) is servo 88: geometry.HORN_AT_90 takes +2 for both eyes. The calibrated ends become -30 / +30, both clean.

## The lid horns' open end (L +52, R +45): accepted, listed

Superseded in part by #189 (below): the teeth are L +13.95, R +6.75, the ends L +52.95, R +45.75, the free travel 62 deg.

- Symptom: the lower lid's back rim 1.3 / 2.0 mm into the servo bracket's front face (z 18) from horn +39, across the
  lid's width; the L upper lid 0.35 mm into the eyeball bar at +52.
- Rejected: a smaller lid tooth (the open ends sit 39 servo deg from 90 on both sides, which tooth 0 would put exactly
  on the model's contact). The calibrated close needs L <= 14.0, R <= 6.8 to shut the lids, and the rest photo
  (model/test_traces.py `test_rest_matches_the_rest_photo`: L -15.2, R -16.3) holds the teeth at L +13, R +6; tooth 0
  would leave the rest lids nearly shut, which the photo does not show.
- Rejected: servo gain. The 9 g servo turns 180 +-10 deg over 500..2500 us (docs/research/2026-10-31-electrical.md 1);
  even 170 deg brings the ends in by 3 deg, short of 13 / 6.
- Rejected: print tolerance. 0.2 mm at the rim is 1.3 deg of lid.
- Guess: the build runs these ends, so the model's lid travel (88 deg free) is short of the build's (93 / 85 servo deg)
  by a shape error in the lower lid's back rim or the servo bracket's front face that no tolerance in the sources
  reaches. Accepted and listed with that reason (model/test_report.py KNOWN_CALIBRATED), not fixed by inventing a part
  shape.

## The jaw bar on the horn arm

- Was: 0.28 mm into the horn arm (the "0.58 across" overstated it), with 0.25 mm left between the bar and the jaw lug.
- Guess: flush seating. With both screws drawn home the bar fills the space between the lug's outer face and the arm's
  underside: moved 0.28 mm inboard (geometry.PT_BAR_PLANES jaw x 84.64 / 71.64) it touches both with nothing inside
  either. mating.INFERRED is empty.

## STEP nominals taken as they are

- Horn seat on the spline: 11.52 past the tab plane (geometry.SERVO_STEP horn_seat). Three independent fits already
  agree with it (docs/research/2026-10-31-shafts.md, Seat).
- Eye horn reach: the bar's horn hole is 12.56 from the shaft against the STEP horn's 12.75 hole; the pin stays 12.75
  and the 0.19 mm is taken up by the bar self-tapping its r 1.05 hole (the mating check passes it, 0.2 allowed).

## Other values

- Servo lead length: 250 mm, the length 9 g micro servo listings publish as typical; Bambu publishes none (the STEP cuts
  the wires). model/electrical.py SERVO_LEAD_MM, the corridors' limit (230 with the 20 mm slack).
- Receiver PWM header numbering: docs/build-photos/eyes-top.jpg shows four leads in the shield's 2 x 2 header block, its
  silkscreen too small to read. Kept the STEP port order (geometry.RECEIVER_STEP). Any other numbering moves a lead's end
  by at most 9.4 mm (the block's diagonal); the tightest eye lead (r_lid, 218.5 of 230) has 11.5 to spare, so no choice
  changes a result.
- Bracket stem depth in the plate (stage 1): the build photos (eyes-lid-linkage-side.jpg, eyes-rest-front.jpg) have
  the bracket's feet flat on the plate top and the stem out of sight in the plate. Superseded by #172: the stem is in the
  plate's slot, not the pan recess, and the desk bracket's stem fills the 5 mm plate, so geometry.STEM_AT stage 1 is
  z -2 (docs/research/2026-11-01-eyes-on-plate.md).

## The joint-end overlaps (#189)

The old engine skipped a lid or eyeball on its bracket pivot (model/engine/run.py PIVOT_PARTNER, now measured) and never
measures the two lids (both move with the horn); #149's
MuJoCo report found them overlapping on the exact meshes at the LIMITS ends, which the build runs without binding.
Measured per pair, one variable at a time, with the designer's meshes swapped in as the cross-check:

- Lower lid into the eye bracket (1.86 mm at +39): our bracket dropped the designer's relief on the band's lower front
  edge (a 45 deg chamfer from y -7.5 on the front face to z 15.5 at y -10, both designer brackets; the designer's lid
  is clean against it). Restored (model/printed/eye_bracket.py LID_RELIEF): clean to +38.
- The two lids at the closed end (1.39 mm at -49): a wrong limit. The lips meet at -30.72 and the shells cannot pass
  each other, so the closed end is the lips; Cansin (#189): the lids close quietly at lid_closed, edges just touching,
  no overlap. The lid teeth go to L 13.95, R 6.75 (inferred: the close lands at -30.75, 0.03 mm of lip), the top of the
  #134 window; the rest photo's face-value lid reading sits 1.2 / 0.9 below, the side its camera tilt moves it.
- The two lids (1.03 mm) and the upper lid on the eye bracket's arm chamfer (0.78 mm) at the open end (+39): the lids'
  ears meet at the back from +32, the upper ear the arm from +35, with the designer's lids and bracket alike. No shape
  in the sources clears them, so the open end is the model's free travel, +31 (geometry.LIMITS); the build's open
  command (L +48, R +41.5) and calibrated ends stay past it, accepted with the servo bracket hit (KNOWN_CALIBRATED).
- Each eyeball into the eye bracket (0.77 mm at +-22): its back rim (z 5) meets the plate's front face (z 13) from
  +-21, the eyeball turning 1.26x the horn (the bar's 12.56 mm horn arm on its 10 mm one); the designer's eyeball and
  bracket alike. The eye limits go to +-20 (free travel). Conflict, recorded: the program commands up to +-25 servo
  degrees and the calibration +-30, which would put the eyeball 1.5..2.5 mm into the plate in the model; the build runs
  them, so the four-bar's gain or the eyeball's back is off by more than any source's tolerance (inferred, unsettled).
