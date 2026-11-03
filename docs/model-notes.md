# Model notes

Decisions that are not in the code. Vocabulary: GLOSSARY.md (Model section); structure: docs/adr/0004.

## Rendering rules (2026-10-31, #47)
- Today's Mech left the model (Cansin, 2026-11-02, #720): its Stages, sub-assemblies and printed parts, their tests,
  renders and the hero live in git history alone; the model holds the next Mech.
- The next Mech is published (Cansin, 2026-11-02, #649, docs/adr/0019): Checks' `Render` shards render its two panels
  and a picture of each of its parts (alone at rest, isometric, framed on its own, 400 x 400: pictures.py next_parts,
  `just pictures next`) and bakes its viewer GLB, a clip per motion it plays since #663 (`just web` with its
  document), when what they are made from changed; the site shows them on [Pictures](pictures.md) and at /viewer/,
  from main. No PR preview (#673). Every published name starts `next-`.
- The next Mech in motion (Cansin, 2026-11-02, #656): its eye gimbal alone sweeping its yaw and pitch with the lids
  following (pictures.py NEXT_MOTIONS, keyed by hand, eased, at the hero's 8 fps, moved by model/gimbal.py moved),
  then each motion it plays, its gestures and Rest as MuJoCo baked them (#663, its rest's blink and its wink in place
  of the keyed ones), each a looping WebP through one camera from the hero's direction, rendered with the rest by
  `just pictures next`; the neck and the jaw join as their tickets move them.
- No screenshots, reference-photo canvases or overlay views: every picture is rendered in Blender (headless, Eevee)
  posed from MuJoCo's baked trajectories (model/trajectories.py `poses`, `just trajectories`; #150): `just render` for
  the panels (each document at rest, a trajectory's first frame);
  code in model/render, output in model/build/pictures. Only what the site shows is rendered (#470). The gestures play
  in the web viewer, not in GIFs (#468); the next Mech's eye gimbal moves in its own (#656).
- Parts carry their Colour group's filament colour in the document's Theme (#805, docs/adr/0022: model/geometry.py
  THEMES and PRINTED, under Numbers from the code below; black drawn a touch lighter so its shading and lines read)
  and their material (geometry.MATERIALS, from the spool's TDS:
  density, and the across-layer values the next Mech's links are held to, model/beams.py, #626). Electronics and servos are
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
  Line Art draws the lines (Freestyle took ~90 % of a frame on one thread), the motions render at the size they ship,
  8 fps, keeping toon timing's key frames (pictures.py at_fps). Tuned for speed (Cansin, 2026-11-02, #470; the render
  profile on #467): Eevee takes blender.py SAMPLES a frame (was 64, then 4) under a hard sun (SUN_ANGLE, so its shadow
  edge needs no samples), the motions render as one animation (one depsgraph), the heaviest meshes are decimated for the
  pictures only (LIGHTER, LIGHTER_FACES; the GLBs keep theirs), Line Art culls back faces, and CI keeps Mesa's shader
  cache.
- Every picture is one WebP with a transparent background, its lines one mid grey (blender.py INK) that reads on the
  site's light and dark pages alike (Cansin, #470, #489: white lines on the dark theme read badly; of three greys
  she took the darkest). No backdrop, disc or tint behind the Mech.
- Panels (Cansin, #470): each document from its left side (+X) and isometric from its front left (+X, -Y, +Z),
  orthographic, every panel at one scale on one ground line, framed tight to the largest silhouette (pictures.py
  VIEWS, PANELS); Pictures shows them in one grid (macros.py next_panels): a column per document, a row per view, each
  linking to its file; on a phone stacked by document.
- The front doors (Cansin, 2026-11-02, #739): the README's top and the site's home show three side by side, as Bones:
  Stage 1 from the front, Stage 3's isometric panel and Stage 3 from the side, exploded by the viewer's offsets
  (pictures.py FRONT, EXPLODE), the two new ones each framed tight on its own at the panels' size and also on Pictures.
- Explode's Parts level (Cansin, 2026-11-03, #811): Pictures shows each Stage in each Skeleton isometric with every
  part apart, framed tight on its own at the panels' size (pictures.py parts_exploded): each part on its sub-assembly's
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
  (CadQuery's threads must not precede a process pool's fork). The model always reads those: `just test` and `just sim`
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
  model/test_trajectories.py; #667). The next Mech's lid drives are certified the same way, the bodies whole, reading
  the exact solids (#655).

## Our model is the source (#88, #97)
- Since `stock-parity` nothing reads docs/references: no gate against the designer's meshes, no vendor STEP meshing,
  no guide sheets. The vendor's files are credits ([Credits](credits.md)), the designer's history (docs/research) only.
- Every picture (`just render`, `just pictures`) draws our geometry (Cansin, 2026-10-31).
- `just stl` (#98): our printed parts as print-ready STLs (mm, 0.02 mm tessellation) in model/build/stl.
- `just step` (#98): every part and envelope, and each document at neutral (model/stages.py's placements, coloured,
  one assembly), as STEP files in model/build/step; `open -a FreeCAD model/build/step/next-mech-back.step`.

## Planned edits (notes only, never in the model; #81)
Cansin's build is the ground truth, then our model (CLAUDE.md). What we plan to change stays here until it stabilises.
- The next Mech (#51; the spec lives there) is designed in the model, as its own documents (geometry.NEXT, #629),
  clean-room: none of today's printed parts or their dimensions, only the Envelopes of the
  hardware we own until its own parts land: linked eyes (one servo for left/right, one for up/down, each eye's
  lids their own), a big head, the redesigned base (boards in the cranium, the pack in the shirt area), a PETG Skeleton (checked
  as PETG HF, geometry.MATERIALS' worst case) wearing a magnet-mounted PLA Skin, Morty or Bart, each in its Theme's
  filaments ([Themes](face-design.md)).
  Its eye gimbal is in (#630, model/gimbal.py, the parts in model/printed/gimbal.py): drawn at rest in the next Mech's documents, moved
  by its own kinematics, its numbers in the next Mech's sim report under "gimbal" (gaze error with every pin's play and
  the pupil's seating, each term beside the total: a pupil keyed with 0.3 mm of seat play, #650; yaw/pitch crosstalk
  beside the Hooke form, the vergence a print error makes, the lids' clearance and range, where they meet shut, the
  lower lid's link angle, the caps' gap, and the lid drives' sweep: each lid, bar, link, horn and shank against the frame and every other part, certified along every line of the
  lid x pitch grid at yaw 0 that turns the pair, #655; the pairs touching at rest checked for overlap at the grid's
  points; and the gimbal's bounding box, servos and horns included, "block_mm", against the compact head's `HEAD_MM`),
  gated in model/test_report.py. Its four servos sit behind the eyes' centres and within their width (#684): the yaw
  servo under the tie-bar, the pitch servo beside the pitch bar, each lid servo under and behind its eye (low and
  forward, so the head's centre of mass stays near the tilt axis), its horn between the eyes (#698). Each eye has an
  upper and a lower lid on that one servo, as today's Mech: the upper lid's crank through the lid bar (a
  parallelogram, bent to pass behind the tie-bar), the lower lid's through a link from a pin on that bar, a crossed
  four-bar turning it against the upper about 0.8x (`gimbal.lower`); shut they meet 4 deg below the eye's middle,
  1.5 deg apart, the lower lid's shell just outside the upper's so tracking a pitch down they pass. Each lid turns on a
  shank from the frame's upright just outside the caps, its spokes behind and under the caps through the whole yaw, so
  the face is as wide as the lids' frame (119 mm, 138 before), each lower lid's boss 0.3 mm off its upright, and `HEAD_MM`'s width is that and a 3 mm shell wall. The pitch push-rod's Hooke coupling is undone by the command map
  `gimbal.servos(yaw, pitch)`, which the noggin service applies once it drives the next Mech; every size is inferred.
  Its Skeleton is drawn in two styles (#704, docs/adr/0020), the Skeleton's values (#805): mechanical and realistic,
  as Bones (GLOSSARY; model/printed/bone.py), and Back is built in each (`next-mech-back`,
  `next-mech-back-mechanical`). As Bones the tie-bar and push-rods (#703, the
  pilot), the yaw yokes (a cradle round the core flaring into the stem at 40 deg, the crank a Bone), the bail (its rod
  and input arm flat-bottomed, its arms round struts), the Torso (round in plan) and the board rack (round corners):
  each prints as drawn (the rack on its back) with no overhang past 45 deg, its bores across the layers where its pins
  are not along Z (the yoke's pitch axle, the bail's three), holds its servo's stall at SF 2 (axial and buckling for the
  tie-bar and push-rods, bending for the crank and the bail's arms; model/printed/test_gimbal.py), its CoACD pieces
  capped (mjcf.MAX_PIECES); so are the lid bars, links and the lids' spokes (#698, each lying in its 3 mm slab, the
  bent lid bar for its bending too). The pitch bar and the frame wait on #704, the neck, head mount, jaw and jaw bar on
  #708 (model/printed UNSTYLED), drawn mechanical in both until then; the core, a ball under its cap, has none.
  In MuJoCo its four servos drive it (#663): the upper lids and the bail through their four-bars, both yokes off the
  yaw horn's tie-bar, each core pitched on its yoke by its push-rod (a universal joint on the bail, a connect at the
  lever's ball), each lower lid by its link (a hinge on the lid bar, a connect at its crank pin, #698). It plays the eye program's gestures and Rest (traces.next_commands): the L eye's position over the
  gimbal's yaw range through `gimbal.servos`, the gaze level (the program has no pitch), each lid level to its edge
  (closed where the lids meet, rest just over the pupil, open) plus the pitch (`lid = rest + k*pitch`, k 1, #51),
  so its sim report reads each servo's torque along them and the clearance is certified along them
  (model/test_trajectories.py). Its neck joins the gaze shifts past ~15 deg (#688): the program's head share under
  the next Mech's calibration (traces.NEXT_CAL, 0.6, inferred), the pan in the eyes' degrees scaled as the yaw and
  through its four-bar (neck.servo_for), the neck Core's writes a frame and a Wi-Fi round trip after the eyes Core's
  (traces.DELAY_MS, 40 ms, inferred), within #51's 2 deg gaze error as the head arrives (model/test_traces.py); the
  gestures' gaze is level, so the tilt carries none.
  Its neck and jaw are in (#641, model/neck.py, the parts in model/printed/neck.py), drawn in the head's frame under the
  gimbal: the head turns on its own pivots (the yoke on the neck mount for pan, the head mount on the yoke's cheeks for
  tilt, straight under the head's centre of mass at rest, the jaw on the head mount's lugs), each servo drives through
  a bar, each busy pivot is a greased M3 shank turning in a Z-printed bore. Its numbers are in the next Mech's sim
  report under "neck" (each bar's transmission angle and servo range, the tilt servo's hold for the head the MJCF
  weighs, the flexing spans' bends), gated in model/test_report.py; every size is inferred. Since #642 it moves in
  MuJoCo (its horns named pan, tilt and jaw horn, so the sim report's neck figures, tip-over and the Core's servo
  names apply) and plays the next hero: the hero's head and jaw keys through its own four-bars (hero.next_at), the one
  motion that turns it, certified for clearance with the gestures (model/test_trajectories.py); since #663 the gimbal
  moves in MuJoCo too and plays the gestures.
- The head variants (#686, model/base.py, the parts in model/printed/base.py, GLOSSARY), in place of #642's two Base
  candidates: one document each (geometry.NEXT), all on one Torso (#685: the
  shirt is the base, a compact open box whose floor is the foot, the neck mount with the pan servo on it and the pack
  lying across behind; its footprint in the sim report's tip_over, footprint_mm). Back: the boards upright on a rack
  screwed under the gimbal frame plate's back edge, behind the eye gimbal, the one variant since Cansin picked it
  (#712: Crown, the boards flat on a shelf over the gimbal, and Split, the switch board low at the back of the neck,
  are gone; the ranking, its marks and the Viewer's buttons stay for the next). Each one's parameters are optimised in
  MuJoCo (model/candidates.py, `python -m model.candidates`; a model test holds the drawn numbers to it): Back's row
  height, for the tilt servo's least worst hold. The sim report gives each one's head box (`variant.head_mm`,
  width x depth x height of what rides the tilt) against #51's 140 x 120 x 150 and how far up it the eyes sit
  (`eyes_up`), and `just sim` ranks them into model/build/reports/next-mech-ranking.json (base.rank: the clearance,
  head-size and four-bar gates, #51's marks, then its criteria in order, each variant's `fails` named), which orders and
  marks the Viewer's buttons ("Back: head size"). A variant whose four-bar opens stays in the model, ranked last; the
  report's gate then holds only the leading variant to it, and fails on anything else, or on a loop the ranking misses
  (#705). Today Back does not fit that head: its boards behind the gimbal make it 141.5 deep, since the head mount
  and the jaw already hang 101 mm under the eyes (eyes_up 0.77, not the lower-middle); the head size stays reported,
  not a hard gate, until #708. Every size is inferred.
- The Stages (#720, geometry.STAGES), for ease of build, each a document in every Skeleton: Stage 1 the eye block (the
  gimbal, its lids and its four servos) on its test stand with the eyes Core (Shield 1, Core 1) standing against the
  stand's back, the stand an open box under the gimbal frame's plate, screwed up through the head mount's holes,
  `base.STAND_H` (40, inferred) tall; Stage 2 the eye block on the Torso's neck (pan, tilt) under the head mount, the
  boards' rack with both Cores and the switch board; Stage 3 adds the jaw and the mouth servo (stages.next_jaw, riding
  the head mount): the whole Mech, the head variant's document, which the ranking and its marks still read. Each plays
  the gestures and Rest; the next hero where the neck is. The viewer has a Stage switch (1, 2, 3, the third marked with
  what it fails), its Skeleton the one the header's Theme bar picks (#805, #806), as on Pictures, whose panels,
  front doors, motions and parts are drawn in every Skeleton and shown in the one picked.
- Today's Mech's non-original choices (#81: the horns' spline teeth, its lead corridors, its bracket stem's depth, its
  horn limits) and its settled conflicts (#172) left the model with it (#720); git history and docs/research keep them.
