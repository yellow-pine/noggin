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
  density, and the across-layer values the Mech's links are held to, model/beams.py, #626). Electronics and servos are
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
  CI's Blender image); without it (the GX10) the bones are left out and the tests marked `bones` skip (#936). The
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
  as PETG HF, geometry.MATERIALS' worst case) wearing a magnet-mounted PLA Skin, Morty, Bart or cansin, each in its
  Palette's filaments ([Themes](face-design.md)).
  Its eye gimbal is in (#630, model/gimbal.py, the parts in model/printed/gimbal.py): drawn at rest in the Mech's documents, moved
  by its own kinematics, its numbers in the Mech's sim report under "gimbal" (gaze error with every pin's play and
  the pupil's seating, each term beside the total: a pupil keyed with 0.3 mm of seat play, #650; yaw/pitch crosstalk
  beside the Hooke form, the vergence a print error makes, the lids' clearance and range, where they meet shut, the
  lower lid's link angle, the caps' gap, and the lid drives' sweep: each lid, bar, link, horn and shank against the frame and every other part, certified along every line of the
  lid x pitch grid at yaw 0 that turns the pair, #655; the pairs touching at rest checked for overlap at the grid's
  points; and the gimbal's bounding box, servos and horns included, "block_mm", against the compact head's `HEAD_MM`),
  gated in model/test_report.py. Its four servos sit behind the eyes' centres and within their width (#684): the yaw
  servo under the tie-bar, hanging under the frame's plate, the pitch servo beside the pitch bar, each lid servo upright
  behind its eye (#838: out of the realistic mandible's ramus; under the eye before), its horn between the eyes (#698).
  Since #901 the eyes are Morty's at life size (#872's round 2): on his pupils, 72.7 mm apart, the cap his eye's 40.4 mm
  sphere, the core, yoke, lever and bail x1.5 with it, the upper lid 1 mm off the cap; each eye's inboard drives (bar,
  link, ears) within 33.75 mm of it, the two eyes' 5.2 mm apart about their shared axis. The bigger lower lids sweep
  under the eyes, so the frame's plate starts behind that sweep (the yokes' bearings reach forward from it) and its bar,
  a beam the face sits on, hangs under it from the lids' uprights; the yaw servo hangs behind it too. Each eye has an
  upper and a lower lid on that one servo: the upper lid's crank through the lid bar (a
  parallelogram, bent to pass behind the tie-bar), the lower lid's through a link from a pin on that bar, a crossed
  four-bar turning it against the upper about 0.8x (`gimbal.lower`; searched again for #901's layout); at rest each
  edge sits on the cap's rim (Morty's outline, 68 deg up and 52 down, lies past the cap's 45); shut they meet 4 deg
  below the eye's middle,
  1.5 deg apart, the lower lid's shell just outside the upper's so tracking a pitch down they pass. Each lid turns on a
  shank from the frame's upright just outside the caps, its spokes behind and under the caps through the whole yaw, so
  the face is as wide as the lids' frame (145 mm since #901), each lower lid's boss 0.3 mm off its upright, and `HEAD_MM`
  is Morty's life-size cranium (160 x 176 x 175 since #901, #893). The pitch push-rod's Hooke coupling is undone by the command map
  `gimbal.servos(yaw, pitch)`, which the noggin service applies once it drives the Mech; every size is inferred.
  Its Skeleton is drawn in two styles (#704, docs/adr/0020), the Skeleton's values (#805): mechanical and realistic,
  as Bones (GLOSSARY; model/printed/bone.py), and Back is built in each (`mech-back`,
  `mech-back-mechanical`). As Bones the tie-bar and push-rods (#703, the
  pilot), the yaw yokes (a cradle round the core flaring into the stem at 40 deg, the crank a Bone), the bail (its rod
  and input arm flat-bottomed, its arms round struts): each prints as drawn with no overhang past 45 deg, its bores across the layers where its pins
  are not along Z (the yoke's pitch axle, the bail's three); so are the lid bars, links and the lids' spokes (#698,
  each lying in its 3 mm slab). Since #708 every other Skeleton part has its Bones too: the pitch, jaw and neck
  bars Bones between their pins, the frame's yaw bearings waisted struts and its uprights round Bones, the neck
  mount's column waisted, the yoke's cheeks Bones, the head mount's flange a chain of Bones flat on the plate from
  screw to screw, the jaw's arms and chin one chain, the Torso's corners round and its walls windowed (lancet heads, so
  it prints upright); the core, a ball under its cap, has none (model/printed UNSTYLED). Every Bone is carved from its mechanical part (#809,
  model/printed/bone.py carved(): the Bones cut to within it, so they add nothing and its interfaces and clearances
  are the mechanical part's; the push-rod's mechanical rod a flat bar round the Bone's waist), or, where a Bone that
  prints as drawn cannot fit inside (the tie-bar, the yaw yoke and the bail), the mechanical part takes it in
  (grown(), its CoACD pieces capped, mjcf.MAX_PIECES). So physics runs on the mechanical documents alone
  (geometry.SIMULATED: the whole Mech and Stage 1): the mechanical parts hold their servo's stall at SF 2 (axial and
  buckling for the tie-bar and push-rods, bending for the crank, the bail's arms and the lid bars;
  model/printed/test_gimbal.py), and the overlap tests, the sweep, the sim and its gates read them; realistic is drawn
  only, its figures the mechanical one's. OCCT fuses Bones unevenly, so model/printed/bone.py chain() draws each on the
  bed domed up and moves it, swells their heads 2% over the spans' ends, and retries a span a hair smaller or the
  other way round until it and its union are valid and keep both heads.
  In MuJoCo its four servos drive it (#663): the upper lids and the bail through their four-bars, both yokes off the
  yaw horn's tie-bar, each core pitched on its yoke by its push-rod (a universal joint on the bail, a connect at the
  lever's ball), each lower lid by its link (a hinge on the lid bar, a connect at its crank pin, #698). It plays the eye program's gestures and Rest (traces.commands): its yaw, in the gimbal's own
  degrees since its servos are Stage 1's (#896), through `gimbal.servos`, the gaze level (the program holds the pitch), each lid level to its edge
  (closed where the lids meet, rest on the cap's rim, open) plus the pitch (`lid = rest + k*pitch`, k 1, #51),
  so its sim report reads each servo's torque along them and the clearance is certified along them
  (model/test_trajectories.py). Its neck joins the gaze shifts past ~15 deg (#688): the program's head share under
  the Mech's calibration (traces.HEAD_CAL, 0.6, inferred), the pan in the eyes' degrees scaled as the yaw and
  through its four-bar (neck.servo_for), the neck Core's writes a frame and a Wi-Fi round trip after the eyes Core's
  (traces.DELAY_MS, 40 ms, inferred), within #51's 2 deg gaze error as the head arrives (model/test_traces.py); the
  gestures' gaze is level, so the tilt carries none.
  Its neck and jaw are in (#641, model/neck.py, the parts in model/printed/neck.py), drawn in the head's frame under the
  gimbal: the head turns on its own pivots (the yoke on the neck mount for pan, the head mount on the yoke's cheeks for
  tilt, under the realistic skull's foramen magnum since #838, the jaw at its condyles on the gimbal frame's lugs, x1.08
  about that hinge since #901 (its drive its size), its servo hanging under the frame's plate behind it), each servo
  drives through
  a bar, each busy pivot is a greased M3 shank turning in a Z-printed bore. Its numbers are in the Mech's sim
  report under "neck" (each bar's transmission angle and servo range, the tilt servo's hold for the head the MJCF
  weighs, the flexing spans' bends), gated in model/test_report.py; every size is inferred. The tilt axis lies 40 mm or
  so behind the head's centre of mass since #838, more than the 9 g servo's rated torque (`sim.RATED_KGF_CM`, its 5 V figure) holds, so a torsion spring on
  its shank balances it (`neck.balance`, `tilt.spring` in the report: wound to the head's weight's turn at rest, its
  rate the turn's change; the MJCF sets it as the tilt pivot's stiffness and springref, the servos' torques count it),
  and the servo holds only what the spring's straight line misses. One spring holds the head in its Skin and bare
  (#830): wound halfway between the two heads' springs, it misses each by half the Skin's turn, which the servo holds
  (`tilt.bare` in the report): a spring for Morty's head alone leaves the bare head past the servo's rating. The neck is a spine since #838: since #858 the neck
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
  room, so no parameter is left to optimise (#708's row height is gone). The sim report gives each one's head box
  (`variant.head_mm`, width x depth x height of what rides the tilt, under the head's shell: `base.shelled`, #828)
  against `gimbal.HEAD_MM` (160 x 176 x 175 since #901, Morty's life-size cranium) and how far up
  it the eyes sit (`eyes_up`, at most `base.EYES_UP`, 0.55: the realistic skull's orbits, a hair over half since #838), both hard gates in each look
  (model/test_report.py, model/printed/test_base.py), and `just sim` ranks them into model/build/reports/mech-ranking.json (base.rank: the clearance,
  head-size, eyes and four-bar gates, #51's marks, then its criteria in order, each variant's `fails` named), which orders and
  marks the Viewer's buttons ("Back: head size"). A variant whose four-bar opens stays in the model, ranked last; the
  report's gate then holds only the leading variant to it, and fails on anything else, or on a loop the ranking misses
  (#705). The shell the gates measure is `base.DOME`, the realistic skull's box (#838; model/skeleton/test_skeleton.py holds
  it to the finished bones), whose bones ride the realistic documents alone.
  Since #838 the realistic Skeleton has bones of its own (docs/adr/0023; since #873 authored in the Skeleton scene,
  model/skeleton/skeleton.blend, docs/adr/0025, and finished there by Blender's Geometry Nodes): 3Demon's cranium and
  mandible scaled to the head's 150 mm height (2 mm spare for the remesh), its orbits on the eyes with the caps 7 mm
  proud, and the atlas and axis at the skull's scale round the post, the atlas under the tilt lugs. `just ours` has Blender
  finish them on a 0.8 mm SDF grid: the cranium shelled to 4 mm, the orbits opened round the lids, every part of the
  realistic Back document cut out 1.6 mm round over each horn's range (what rides with the bone, exactly), crumbs
  under 2% of the bone dropped, meshed at the grid's zero level into one piece each.
  Morty cannot be worn over the full skull (its back 18 mm past his, its brow 10 mm ahead of his face), so the skull and
  mandible are also carved 1.6 mm round every Skin's Shells (`geometry.WORN`, Cansin's pick): the documents, which wear
  a Skin, carry the worn copies, the pictures' bare look the full ones (`pictures.bare`); both print. Back fits since #708 (136 x 117.3 x 149.8 in both Skeletons since #828, the Bones carved inside, eyes_up
  0.497; #708's was 118.6 x 115.8 x 149.3, before it 120 x 134.5 x 129.5, eyes_up 0.78): the stack
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
