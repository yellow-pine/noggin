# Model notes

Decisions that are not in the code. Vocabulary: GLOSSARY.md (Model section); structure: docs/adr/0004.

## Rendering rules (2026-10-31, #47)
- The Mech is published (Cansin, 2026-11-02, #649, docs/adr/0019): Checks' `Render` (one job since #898, its
  parts and trajectories built once) renders its six stills (`just pictures all`) and bakes its viewer GLB, a clip per motion it plays since #663 (`just web` with its
  document), when what they are made from changed; the site shows them on [Pictures](pictures.md) and at /viewer/,
  from main. No PR preview (#673).
- Stills alone (Cansin, 2026-11-03, #839): Blender renders no motion, no animated WebP or GIF (the eye gimbal's
  motions of #656 and #663 are gone). The Mech moves in the web viewer alone, which Pictures embeds once per
  motion (macros.py motions) and the front doors' stills link to, deep-linked to their Stage, Explode level and
  Preset.
- No screenshots, reference-photo canvases or overlay views: every picture is rendered in Blender (headless, Eevee)
  posed from MuJoCo's baked trajectories (model/trajectories.py `poses`, `just trajectories`; #150): `just render` for
  the six stills (#898: the front doors and a poster per Stage);
  code in model/render, output in model/build/pictures. Only what the site shows is rendered (#470). The gestures play
  in the web viewer, not in GIFs (#468, #839).
- Parts carry their Colour group's filament colour in the Preset's Palettes (#805, #819, docs/adr/0022: model/geometry.py
  THEMES, PRESETS and PRINTED; a GLB in its Shape's first Preset's, each material named by its Colour group, which the
  viewer repaints; under Numbers from the code below; black drawn a touch lighter so its shading and lines read)
  and their material (geometry.MATERIALS, from the spool's TDS:
  density, and the across-layer values the Mech's links are held to, model/beams.py, #626). The sim weighs a printed
  part as it prints, a 0.85 mm skin round a 15% infill core (the slicer's default process,
  docs/research/2026-11-26-print-infill.md; model/mjcf.py mass(), #1003; inferred, Cansin's slicer settings aren't
  recorded). Electronics and servos are
  neutral greys, darker for the boards (model/render/scene.py GREYS).
- `just view` (MuJoCo's viewer, local checks only; Cansin kept it 2026-11-01, model/test_mjcf.py pins it and CI
  renders it offscreen): headlight ambient 0.5, diffuse 0.5, specular 0; black and white pulled in
  (model/mjcf.py VIEW), the rest their filament's colour; a flat sky in the pictures' background. Added in #150, merged on green: a directional key
  light from the Mech's upper front-left casting shadows (diffuse and specular 0.3) and satin parts (specular 0.3,
  shininess 0.5).
- Look (Cansin's pick, style B): satin plastic (roughness 0.45, low specular) mixed 45/55 with a two-step toon
  shadow and one small highlight band, grey lines on silhouettes and creases (faces more than 60 degrees apart, so
  STL facets draw none; their width blender.py ART_PX in the pictures, LINE_PX in the web viewer), one key light at the camera's upper right, a transparent background. STL facets are
  smoothed by angle (35 degrees) with weighted normals; pupils are lifted 0.3 mm off the eyeball so their outline stays
  whole. For CI's software GL (Cansin, 2026-11-01, #226, #276; docs/research/2026-11-01-render-profile.md): Blender's
  Line Art draws the lines (Freestyle took ~90 % of a frame on one thread). Tuned for speed (Cansin, 2026-11-02, #470; the render
  profile on #467): Eevee takes blender.py SAMPLES a frame (was 64, then 4) under a hard sun (SUN_ANGLE, so its shadow
  edge needs no samples), the heaviest meshes are decimated for the
  pictures only (LIGHTER, LIGHTER_FACES; the GLBs keep theirs), Line Art culls back faces, and CI keeps Mesa's shader
  cache.
- Every picture is one WebP with a transparent background, its lines one mid grey (blender.py INK) that reads on the
  site's light and dark pages alike (Cansin, #470, #489: white lines on the dark theme read badly; of three greys
  she took the darkest). No backdrop, disc or tint behind the Mech.
- Six stills alone (Cansin, 2026-11-04, #889, #898): the front doors below and a poster per Stage (pictures.py
  POSTERS: each Stage at rest in the default Preset, isometric from its front left (+X, -Y, +Z), orthographic, the three
  at one scale on one ground line, framed tight to the largest silhouette, a viewer's still until it loads). Every
  other picture is a viewer embed (macros.py viewers): Pictures shows each Stage from the side (+X), isometric and at
  Explode's Parts level (stage_views), and each part alone, the rest ghosted (part_pictures).
- The front doors (Cansin, 2026-11-02, #739): the README's top and the site's home show three side by side, in the
  default Preset, the Default build (#819), whichever Preset is picked, its mechanism bare of every Shell until a finished
  Skin exists (Cansin, 2026-11-03, #843: pictures.py bare): Stage 1 from the front, Stage 3 isometric and Stage 3 from
  the side, exploded by the viewer's offsets (pictures.py FRONT, EXPLODE), each framed tight on its own at the posters'
  size and also on Pictures.
- Explode's Parts level (Cansin, 2026-11-03, #811): the viewer's `explode=2`, each part on its sub-assembly's
  offset (EXPLODE) slid out along its Assembly direction (pictures.py directions: a servo and its horn along the shaft,
  a part on a pivot or rod joint along its axis away from the Stage's middle, a board or the pack off its seat) until
  its bounding box is GAP clear of its own and of every part placed before it, the largest first (pictures.py offsets,
  which the viewer's GLBs carry too). The front doors keep the Sub-assemblies level.
- Real photos of the build are local only (docs/references/build-photos, gitignored): ground truth for the model, never in git, the README or the site (Cansin, 2026-11-01: no staged photos yet).

## Numbers from the code

The picture sizes and the colours, as model/render/pictures.py and blender.py, model/geometry.py THEMES and
model/mjcf.py VIEW set them.

<!--{{ pictures }}-->

<!--{# GitHub shows the line below; the site drops it for the tables above, which it builds from the code -->
They are in [the tables on the site](https://yellowpine.com/noggin/docs/model-notes/#numbers-from-the-code).
<!-- #}-->

## Our printed parts (#50)
- Every printed part gets an independent parametric CadQuery design in model/printed/: interfaces exact, registered
  in `model/printed/__init__.py` PARTS by our part name (GLOSSARY.md).
- Each part has a test beside it probing the solid at its interfaces (holes, pins, pivots, mount faces).

## Our hardware envelopes and CI (#58)
- model/envelopes.py draws a simple CadQuery envelope of each piece of hardware (servo, horn, Shield, Core, switch
  board, battery) in its STEP frame, with the interfaces (tab holes, shaft, mount holes, connectors) at the STEP's
  numbers (model/test_envelopes.py).
- `just ours` (model/ours.py) writes every printed part and envelope to model/build/ours as STLs, in its own process
  (CadQuery's threads must not precede a process pool's fork), then has Blender finish the realistic Skeleton's bones
  round them from the Skeleton scene (model/skeleton, docs/adr/0025) where Blender is (`just linux-test` runs in
  CI's Blender image). The native GX10 worker also runs Blender and the finished-bone checks (#979); a host without
  Blender still leaves the bones out and skips tests marked `bones`. The
  model always reads those: `just test` and `just sim`
  build them first, and the reports are simulated on our geometry; CI builds them (never committed) and the site
  publishes main's at /reports (docs/adr/0009).

## Gates (#627)
- Each four-bar's singularity margin and transmission angle over its horn's sweep, in the sim report's `loops`
  (model/gates.py loops, model/mujoco_report.py): the margin keeps a 0.1 mm pin fit's play under 2 deg, the angle stays
  at 40 deg or more, any exception listed with its reason (model/test_report.py KNOWN_TRANSMISSION).
- Every pair of parts certified clear at every step of each motion (the gestures, Rest and the hero), not only at the
  100 ms frames:
  each pair of their convex pieces read at the ends of a span (the bounding spheres' gap, `mj_geomDistance` only where
  that is too close), halved where the two pieces could move further than that, and a pair of pieces whose hinges all
  turn about one point skipped while their distances from it keep them apart (model/gates.py certify,
  model/test_trajectories.py; #667). The Mech's lid drives are certified the same way, the bodies whole, reading
  the exact solids (#655).

## Our model is the source (#88, #97)
- Since `stock-parity` nothing reads docs/references: no gate against the designer's meshes, no vendor STEP meshing,
  no guide sheets. The vendor's files are credits ([Credits](credits.md)), the designer's history (docs/research) only.
- Every picture (`just render`, `just pictures`) draws our geometry (Cansin, 2026-10-31).
- `just stl` (#98): our printed parts as print-ready STLs (mm, 0.02 mm tessellation) in model/build/stl.
- `just step` (#98): every part and envelope, and each document at neutral (model/stages.py's placements, coloured,
  one assembly), as STEP files in model/build/step; `open -a FreeCAD model/build/step/mech-back.step`.

## Cansin's parts (2026-10-31, #51)
What Cansin owns and has ordered, by our names (the codes are on [Parts](build/parts.md#parts-to-buy)):
- Owned: the Beginner Hardware Kit (2 Cores, a Shield and a transmitter shield, a switch board, a pack, its charger,
  one 180° and one 360° servo), the Battery Upgrade Kit (a second switch board and pack), 4 servos, M3x10, M2x12 and
  M2 nuts (20 each); PLA Pure in Milky Pink, Pure White, Absolute Black and Apricot (docs/research/2026-10-31-filament.md),
  and black PETG.
- Ordered 2026-10-31: a Shield, 3 servos and a pack.
- Spare once the Mech has its 7 servos, 2 Cores, 2 Shields, a switch board and a pack: a pack on charge (the charger
  off the Mech) and a switch board.

## Planned edits (notes only, never in the model; #81)
The model is the ground truth, then the Mech you build (CLAUDE.md). What we plan to change stays here until it stabilises.
- The Mech (#51; the spec lives there) is designed in the model, as its own documents (geometry.MECH, #629),
  clean-room: none of today's printed parts or their dimensions, only the Envelopes of the
  hardware we own until its own parts land: linked eyes (one servo for left/right, one for up/down, each eye's
  lids their own), a big head, the redesigned base (boards in the cranium, the pack in the shirt area), a PETG Skeleton (checked
  as PETG HF, geometry.MATERIALS' worst case) wearing a magnet-mounted PLA Skin in its Palette's filaments
  ([Themes](face-design.md)): Morty's, cut from his sculpt by `model/morty/shells.py` (docs/adr/0028). *Upcoming (#850):
  its Seats.*
  Its eye gimbal is in (#630, model/gimbal.py, the parts in model/printed/gimbal.py): drawn at rest in the Mech's documents, moved
  by its own kinematics, its numbers in the Mech's sim report under "gimbal" (gaze error with every pin's play and
  the pupil's seating, each term beside the total: a pupil keyed with 0.3 mm of seat play, #650; yaw/pitch crosstalk
  beside the Hooke form, the vergence a print error makes, the lids' clearance and range, where they meet shut, the
  lower lid's link angle, the caps' gap, and the lid drives' sweep: each lid, bar, link, horn and shank against the frame and every other part, certified along every line of the
  lid x pitch grid at yaw 0 that turns the pair, #655; and the pairs touching at rest checked for overlap at the grid's
  points), gated in model/test_report.py. Its four servos sit behind the eyes' centres and within their width (#684): the yaw
  servo under the tie-bar, hanging under the frame's plate, the pitch servo beside the pitch bar, each lid servo upright
  behind its eye (#838: out of the realistic mandible's ramus; under the eye before), its horn between the eyes (#698).
  Since #967's re-layout each lid servo stands behind the belt its eye's drives will leave the eye's sphere through
  once the lids stow under Morty's skin (its horn's axis 56.5 mm behind the eye, 37 before, where its case stood
  across that belt; its collar stands on a shelf under its case, out to a post outboard of the hub, which lies on
  the cranium tray's riser under the R one), and the pitch drive rises over it: each push-rod leans 29 deg down to the back, from the lever's
  ball to a ball on a bail arm that hangs forward of the bail's axis, which stands 51 mm behind and 24 mm over the
  eyes, over the lid servos and under the cranium tray; the pitch servo and its horn stay, their bar leans. The
  core's top is cut to a cone round the lever where the rod passes, and the lever's neck leans forward, square to the
  rod's bed. The rod meets its lever at 52 deg or more and the bar its horn at 53, so the gaze's play counts each
  pitch pin through the angle its link meets its arm at (1.76 deg with the pupil's seating).
  Since #901 the eyes are Morty's at life size (#872's round 2), since #967 on his Sculpt's own eyeballs, each a
  sphere fitted to its dome: 73.3 mm apart, a 37.1 mm ball (his pupils sit 9 deg outward on it; the domes' feet, seen
  from the front, are 80 mm apart, as each dome faces outward). The eyes are sunk (Cansin, 2026-11-28, ADR 0028):
  the hidden lids and their cap sweep a shell 34.9 to 36.7 mm from each eye's centre (`gimbal.LIDS_SHELL`: the cap a
  34.9 mm sphere, 2.2 mm under his eye's; the lids' band 0.55 mm over it and 0.75 mm thick, its outer face 0.9 mm
  under his eye's own surface, so 0.4 mm of the face's wall reaches each opening's outline over it, #850). The core,
  its seat and the yoke are x1.3 of the gimbal's first 27 mm, sized to that cap, so the yoke's crank and the tie-bar's
  fingers leave the yaw bearing's pad its depth inside the shell; the lever keeps its 23.8 mm, which the pitch drive
  is laid out from. The cap is solid in front, on
  the core's seat, and from there a 1.6 mm shell out to its opening's own outline as the front sees it; below the
  eye line it ends 2.2 mm inside the outline, on the rim's own way out from the eye's centre, since pitched down a
  cap that filled it met the yaw bearing. Nothing else may cross that shell but
  in the belt behind the eye, between the two stowed lids, and between the eyes, where the lids' hubs are, so the yaw
  drive is laid out round it: each yoke has no
  stem, its crank lies at its bottom bar's level, and it turns on a post on its yaw bearing, a pad and a web inside
  the shell that run back and 25 deg inboard from under the yoke, leave the shell through the belt by a neck and stand
  on a buttressed pylon on the plate (`model/printed/gimbal.py` `rail`; it holds SF 2 with the eye held against the
  pitch servo's stall, where a 1.5 mm strip of the sphere alone read 0.2); the tie-bar reaches each yoke's crank pin
  by a finger, under the crank, back and up inside the shell and level out through the belt to a cross-bar behind the
  eyes, with a tail down the midline to the yaw horn's pin, which stays with its horn and servo (the finger is as
  thick as the cross-bar where the stalled servo twists it: SF 3.3). Each keeps 1.9 mm or more from what it passes,
  on the exact solids, and neither shares volume with the shell (`model/printed/test_gimbal.py`). The frame's plate
  starts behind the eyes and its bar, a beam the face sits on, hangs under them from a foot behind each cheek; the
  yaw servo hangs behind it too. Since #967 the frame hides inside Morty's Skin: the beam ends inside his cheeks, its
  lower outer corners cut back, and an arm runs back from each end to its foot,
  so the frame and the eyes' drives lie a Shell's wall and its clearance inside Morty's Sculpt at rest and over each
  eye servo's range (model/review/test_hidden.py, on the Sculpt git holds, in every run of the Model's tests; over the
  head's turns it reads the private reference's regions, with the review's checks). A
  window through the plate either side of the yaw servo's collar lets the realistic skull's maxillae up from the
  palate to the cranium's base, so the bare skull is one piece (`gimbal.WINDOW_X`). Each eye has an
  upper and a lower lid on that one servo, hidden under his skin since #967 (Cansin, 2026-11-28): both in the one
  band, in his face's filament. Open, at the servo's centre, the lower lid's edge lies along the bottom rim where
  the cap's bottom edge shows, cut to the rim's curve as the front sees it (the sliver of lid under the cap, 2.2 mm),
  and the upper lid's, the same curve, is parked behind the top rim; shut they meet on that curve lifted, 6.5 deg
  over the eye's middle, 0.6 mm apart. The lower lid turns 63.5 deg and the upper 75.2, read off the eye whites' cuts
  on his Sculpt, and the servo has 4.5 deg more to open them wider, which the eye program's lid map needs over its
  rest (a blink takes about 0.7 s: the servo's slew over 75 deg). Each lid covers 4 deg past the rim it hides behind; the upper lid's back edge is the top rim itself
  for 5 mm either side of the eye's middle, where the bail's arm comes. The upper lid's crank is driven through the
  lid bar (a parallelogram), the lower lid's through a link from the lid horn's inner hole to a crank pointing down,
  a crossed four-bar turning it against the upper (`gimbal.lower`; its link meets its crank at 55 deg or more). All
  four lids turn on one shank along the eye line, in a wall of the frame on the midline, each on a sleeve between
  the eyes; a spoke runs from each sleeve back to a tail of its lid's band, behind everything the cap's shell sweeps
  as its eye yaws in. No lid has a bearing at its outer end. The pitch push-rod's Hooke coupling is undone by the command map
  `gimbal.servos(yaw, pitch)`, which the noggin service applies once it drives the Mech; every size is inferred.
  Its Skeleton is drawn in two styles (#704, docs/adr/0020), the Skeleton's values (#805): mechanical and realistic,
  as Bones (GLOSSARY; model/printed/bone.py), and Back is built in each (`mech-back`,
  `mech-back-mechanical`). As Bones the push-rods (#703, the
  pilot), the yaw yokes (a cradle round the core flaring from its flat foot at 40 deg, the crank a Bone), the bail (its rod
  and input arm flat-bottomed, its arms round struts): each prints as drawn (the leaned push-rod and the bail on their
  own beds, `rod_bed` and `bail_bed`, #967) with no overhang past 45 deg, its bores across the layers where its pins
  are not along Z (the yoke's pitch axle, the bail's three); so are the lid bars, links and the lids' spokes (#698,
  each lying in its 3 mm slab). Since #708 every other Skeleton part has its Bones too: the pitch, jaw and neck
  bars Bones between their pins, the frame's uprights round Bones, the neck
  mount's column waisted, the yoke's cheeks Bones, the head mount's flange a chain of Bones flat on the plate from
  screw to screw, the jaw's arms and chin one chain, the Torso's corners round and its walls windowed (lancet heads, so
  it prints upright), the tie-bar (#1052: its cross-bar a Bone on its print bed, the cross-bar's back edge, each finger a chain of
  three Bones in its slab and the tail one, each as wide as its flat arm so the arm's sides cut it); the core, a ball under its cap, has none (model/printed UNSTYLED). Every Bone is carved from its mechanical part (#809,
  model/printed/bone.py carved(): the Bones cut to within it, so they add nothing and its interfaces and clearances
  are the mechanical part's; the push-rod's mechanical rod a flat bar round the Bone's waist), or, where a Bone that
  prints as drawn cannot fit inside (the yaw yoke and the bail), the mechanical part takes it in
  (grown(), the bail's CoACD pieces capped, mjcf.MAX_PIECES). So physics runs on the mechanical documents alone
  (geometry.SIMULATED: the whole Mech and Stage 1): the mechanical parts hold their servo's stall at SF 2 (axial and
  buckling for the push-rods, bending for the crank, the bail's arms and the lid bars, bending and torsion for the
  tie-bar's fingers and tail, bending for the yaw bearings;
  model/printed/test_gimbal.py), and the overlap tests, the sweep, the sim and its gates read them; realistic is drawn
  only, its figures the mechanical one's. OCCT fuses Bones unevenly, so model/printed/bone.py chain() draws each on the
  bed domed up and moves it, swells their heads 2% over the spans' ends, and retries a span a hair smaller or the
  other way round until it and its union are valid and keep both heads.
  In MuJoCo its four servos drive it (#663): the upper lids and the bail through their four-bars, both yokes off the
  yaw horn's tie-bar, each core pitched on its yoke by its push-rod (a universal joint on the bail, a connect at the
  lever's ball), each lower lid by its link off the lid horn's inner hole, a four-bar of its own (#967). It plays the eye program's gestures and Rest (traces.commands): its yaw, in the gimbal's own
  degrees since its servos are Stage 1's (#896), through `gimbal.servos`, the gaze level (the program holds the pitch), each lid level to its edge
  (closed where the lids meet; rest and open both open, hidden behind the opening's rim, #967),
  so its sim report reads each servo's torque along them and the clearance is certified along them
  (model/test_trajectories.py). Its neck joins the gaze shifts past ~15 deg (#688): the program's head share under
  the Mech's calibration (traces.HEAD_CAL, 0.6, inferred), the pan in the eyes' degrees scaled as the yaw and
  through its four-bar (neck.servo_for), the neck Core's writes a frame and a Wi-Fi round trip after the eyes Core's
  (traces.DELAY_MS, 40 ms, inferred), within #51's 2 deg gaze error as the head arrives (model/test_traces.py); the
  gestures' gaze is level, so the tilt carries none.
  Its neck and jaw are in (#641, model/neck.py, the parts in model/printed/neck.py), drawn in the head's frame under the
  gimbal: the head turns on its own pivots (the yoke on the neck mount for pan, the head mount on the yoke's cheeks for
  tilt, under the realistic skull's foramen magnum since #838, the jaw at its condyles on the gimbal frame's lugs, its servo
  hanging under the frame's plate behind it; since #968
  its carrier a chain of Bones inside the mandible, measured on the bone, its bar, horn and servo inboard of the left
  ramus), each servo
  drives through
  a bar, each busy pivot is a greased M3 shank turning in a Z-printed bore. Its numbers are in the Mech's sim
  report under "neck" (each bar's transmission angle and servo range, the tilt servo's hold for the head the MJCF
  weighs, the flexing spans' bends), gated in model/test_report.py; every size is inferred. The head's centre of mass
  hangs in front of the tilt axis, so since #978 the standard tilt servo turns it through a reduction four-bar (a
  short crank on the moving case, a longer arm on the fixed carrier, `neck.TILT_ARMS`; the report's `tilt.gain`): the head
  turns about half the servo's turn, so the servo holds the head in its Skin and bare (`tilt.bare`) under
  its rating with no balance spring. The MJCF hangs the bar on the crank's pin and closes it on the carrier's anchor,
  so the transmission gate reads the bar against the carrier's arm, the angle the moving case sees. Since #1039 the
  neck lies under a skin that moves (docs/adr/0030): Morty's skin above the collar rides the head, so the neck
  tube (one aluminium tube since #1075, docs/adr/0031: the neck socket holds its foot on the Torso's floor, the
  cervical carrier rides its top) runs straight up the canal to its top, between where the nape's and the throat's
  rims swing as the head nods, and the tilt lever's arm steps inboard round its horn, nearer the pan axis as the pan swings it
  across the nape; every part of the neck lies a Shell's wall and its clearance under that skin through tilt and pan
  together (model/review/test_nape.py, on the Sculpt git holds). The neck is a spine since #838: since #858 the neck
  mount's hollow post (20 mm) rises from the Torso's floor through its lid, the pan servo on it over the lid and the
  pan at its top, the yoke's disc under its top floor and the tilt servo under the head, the cheeks short from there;
  the neck cable runs up inside the post and out over the lid into the pan's flexing span; the Torso a box pedestal 120 x 116 x 52 with its own lid sunk flush inside its walls, as the picture
  Cansin gave (a plaque in front, a border round the lid's panel, as Bones). Since #642 it moves in
  MuJoCo (its horns named pan, tilt and jaw horn, so the sim report's neck figures, tip-over and the Core's servo
  names apply) and plays the hero: the hero's head and jaw keys through its own four-bars (hero.keys_at), the one
  motion that turns it, certified for clearance with the gestures (model/test_trajectories.py); since #663 the gimbal
  moves in MuJoCo too and plays the gestures.
- The head variants (#686, model/base.py, the parts in model/printed/base.py, GLOSSARY), in place of #642's two Base
  candidates: one document each (geometry.MECH), all on one Torso (#685: the
  shirt is the base, a compact open box whose floor is the foot, the neck mount's post rising from it, the pack
  lying across behind, the switch board lying flat beside the pack's lead end (#828) and, since #858, the power-path
  board flat in front of the neck and nothing else; its footprint in the sim report's tip_over, footprint_mm).
  Back (#828 stood a Core on edge in each cheek, #838 moved them down into the Torso, #858 up into the realistic
  skull's cranium, lying flat on their Shields on the cranium tray, the hub low at the back of the skull base, its
  port the head's; #708 stood the boards upright over the eyes; Cansin read it as a tuft of hair), the one variant since Cansin picked it
  (#712: Crown, the boards flat on a shelf over the gimbal, and Split, the switch board low at the back of the neck,
  are gone; the ranking, its marks and the Viewer's buttons stay for the next). Its boards sit where the cranium and the Torso have
  room, so no parameter is left to optimise (#708's row height is gone). What holds the head's mechanism in the head
  is Morty's skin, his Sculpt's surface (docs/adr/0027, #1089): every part of it at least 2.1 mm under that (a
  Shell's 1.6 mm wall and 0.5 mm of clearance), at rest and through its motion, in both Skeletons, read on the Sculpt
  git holds by model/review's tests: test_hidden.py the eye gimbal over each eye servo's range, test_nape.py the neck
  under the skin that rides the head through tilt and pan, test_head.py the cranium tray, its boards and the jaw
  against the head's skin and the jaw's as the jaw opens. The compact head's box (160 x 176 x 175 mm, `gimbal.HEAD_MM`,
  with `base.DOME` and `base.EYES_UP`) measured it before and is gone, with the report's head box and eye height and
  the gimbal's bounding box. Where a part does not fit under his skin the mechanism moves, never the skin; the jaw
  carrier's chin end did (#968: its chains met 1.88 mm under his chin's skin and swung through the skin under it as
  the jaw opened; now a bar across behind the symphysis' front wall, 6 mm or more from both). `just sim` ranks the variants into model/build/reports/mech-ranking.json
  (base.rank: the clearance and four-bar gates, #51's marks, then its criteria in order, each variant's `fails`
  named), which orders and marks the Viewer's buttons ("Back: clearance"). A variant whose four-bar opens stays in the
  model, ranked last; the report's gate then holds only the leading variant to it, and fails on anything else, or on
  a loop the ranking misses (#705). The bones ride the realistic documents alone.
  Since #838 the realistic Skeleton has bones of its own (docs/adr/0023; since #873 authored in the Skeleton scene,
  model/skeleton/skeleton.blend, docs/adr/0025, and finished there by Blender's Geometry Nodes): since #874
  BodyParts3D's skull, mandible and C1 to C7, each region resized uniformly (about life-size) and warped by one
  smooth field (model/skeleton/fit.py) within the confirmed local length budget: the orbits on the eyes, the
  condyles on the jaw's hinge, the occipital condyles on the tilt axis, the vertebrae down the cervical canal's path,
  the atlas round the pan axis, and every bone at least 2.1 mm under Morty's skin, the Sculpt's surface
  (model/skeleton/envelope.py, docs/adr/0025: the skull's limit where the compact head's box was), the cranium drawn
  out toward it so the vault closes over the mechanism. The vertebrae keep that under his neck's skin as it rides the
  head through tilt and pan (docs/adr/0030), for which C5 and C6 alone are slimmed toward their canals, past the
  budget, in zones declared on the original anatomy (model/skeleton/budget.py). `just ours` has Blender
  finish them on a 0.8 mm SDF grid: the vault's bones thickened inward to at least 2.4 mm (the parietals are
  thinner at the temples), the skull's 21 bones sealed into one across every gap under 3 mm, the cranium
  shelled to 4 mm, the orbits opened round the lids, every part of the
  realistic Back document cut out 1.6 mm round over each horn's range (what rides with the bone, exactly), crumbs
  under 2% of the bone dropped, meshed at the grid's zero level into one piece each.
  The skull and mandible are also carved 1.6 mm round a Skin's Shells (`geometry.WORN`, Cansin's pick), the eyeball
  caps alone while they are the only Shells a document wears: the documents carry the worn copies, the pictures' bare look the full
  ones (`pictures.bare`); both print. Since #708 the stack
  under the eyes shrank from 101 mm to 74.5, the tilt axis 0.5 mm under the gimbal frame's plate with the cheeks'
  bosses up into the head mount's flange and the whole neck 6 mm shorter, the jaw hinged beside the tilt lugs with its
  arms under the flange, its servo lying on the plate's front beside the mouth, the tilt span's head clamp straight
  behind the axis. Every size is inferred.
- The Stages (#720, geometry.STAGES), for ease of build, each a document in every Skeleton shape: Stage 1 the eye block (the
  gimbal, its lids and its four servos) on its test stand with the eyes Core (Shield 1, Core 1) standing against the
  stand's back, the stand an open box under the gimbal frame's plate, screwed up through the head mount's holes,
  `base.STAND_H` (40, inferred) tall; Stage 2 the eye block on the Torso's neck (pan, tilt) under the head mount, both
  Cores in the cranium, the switch board in the Torso; Stage 3 adds the jaw and the mouth servo (stages.jaw_sub, riding
  the head mount): the whole Mech, the head variant's document, which the ranking and its marks still read. Each plays
  the gestures and Rest; the hero where the neck is. The viewer has a Stage switch (1, 2, 3, the third marked with
  what it fails), its Shapes and Palettes the Preset's the header's Theme bar picks or its own mix (#805, #806, #819);
  Pictures' panels are drawn in every Preset and shown in the one picked, each part in its
  Shape's first Preset.
