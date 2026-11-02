# Model notes

Decisions that are not in the code. Vocabulary: GLOSSARY.md (Model section); structure: docs/adr/0004.

## Rendering rules (2026-10-31, #47)
- Not published (Cansin, 2026-11-02, #640, docs/adr/0019): today's parts derive from the designer's models, so until
  the clean-room Mech (#51) the pictures, the hero and the viewer's GLBs are rendered locally alone (`just render`,
  `just hero`, `just web`); CI renders none and neither the site nor the README shows them. The rules below are how
  they are made.
- The next Mech is published (Cansin, 2026-11-02, #649, docs/adr/0019): Checks' `Blender` job renders its two panels
  and a picture of each of its parts (alone at rest, isometric, framed on its own, 400 x 400: pictures.py next_parts,
  `just pictures next`) and bakes its viewer GLB, still, without clips (`just web` with its document), when what they
  are made from changed; the site shows them on [Pictures](pictures.md) and at /viewer/. A PR that changes them gets
  the `preview` artifact: the live site's panels above its own in one before-after.webp, and its pictures (`just
  preview <pr>` downloads it). Every published name starts `next-`.
- The next Mech in motion (Cansin, 2026-11-02, #656): its eye gimbal alone sweeping its yaw and pitch with the lids
  following, a blink and a wink (pictures.py NEXT_MOTIONS, keyed by hand, eased, at the hero's 8 fps), each a looping
  WebP through one camera from the hero's direction, rendered with the rest by `just pictures next`. The gimbal's own
  kinematics move it (model/gimbal.py moved) until its MuJoCo document drives it; the gestures join once the next Mech
  plays them, the neck and the jaw as their tickets land. A motion the PR changed gets before-after-<motion>.webp in the
  preview, the live one above the PR's, frame by frame.
- No screenshots, reference-photo canvases or overlay views: every picture is rendered in Blender (headless, Eevee)
  posed from MuJoCo's baked trajectories (model/trajectories.py `poses`, `just trajectories`; #150): `just render` for
  the Stage panels (each Stage at rest, a trajectory's first frame), `just hero` for the hero;
  code in model/render, output in model/build/pictures. Only what the site shows is rendered (#470). The gestures play
  in the web viewer, not in GIFs (#468); the next Mech's eye gimbal moves in its own (#656).
- Parts carry their real spool's colour (PLA: model/geometry.py SPOOLS/PRINTED, under Numbers from the code below; Absolute Black
  drawn a touch lighter so its shading and lines read) and its material (geometry.MATERIALS, from the spool's TDS:
  density, and the across-layer values model/beams.py checks, #626). Electronics and servos are
  neutral greys, darker for the boards (model/render/scene.py GREYS).
- `just view` (MuJoCo's viewer, local checks only; Cansin kept it 2026-11-01, model/test_mjcf.py pins it and CI
  renders it offscreen): headlight ambient 0.5, diffuse 0.5, specular 0; Absolute Black and Pure White pulled in
  (model/mjcf.py VIEW), the rest their spool's colour; a flat sky in the pictures' background. Added in #150, merged on green: a directional key
  light from the Mech's upper front-left casting shadows (diffuse and specular 0.3) and satin parts (specular 0.3,
  shininess 0.5).
- Look (Cansin's pick, style B): satin plastic (roughness 0.45, low specular) mixed 45/55 with a two-step toon
  shadow and one small highlight band, grey lines on silhouettes and creases (faces more than 60 degrees apart, so
  STL facets draw none; their width blender.py ART_PX in the pictures, LINE_PX in the web viewer), one key light at the camera's upper right, a transparent background. STL facets are
  smoothed by angle (35 degrees) with weighted normals; pupils are lifted 0.3 mm off the eyeball so their outline stays
  whole. For CI's software GL (Cansin, 2026-11-01, #226, #276; docs/research/2026-11-01-render-profile.md): Blender's
  Line Art draws the lines (Freestyle took ~90 % of a frame on one thread), the hero renders at the size it ships,
  8 fps, keeping toon timing's key frames (pictures.py at_fps). Tuned for speed (Cansin, 2026-11-02, #470; the render
  profile on #467): Eevee takes blender.py SAMPLES a frame (was 64, then 4) under a hard sun (SUN_ANGLE, so its shadow
  edge needs no samples), the hero renders as one animation (one depsgraph), the heaviest meshes are decimated for the
  pictures only (LIGHTER, LIGHTER_FACES; the GLBs keep theirs), Line Art culls back faces, and CI keeps Mesa's shader
  cache.
- Every picture is one WebP with a transparent background, its lines one mid grey (blender.py INK) that reads on the
  site's light and dark pages alike (Cansin, #470, #489: white lines on the dark theme read badly; of three greys
  she took the darkest). No backdrop, disc or tint behind the Mech.
- Stage panels (Cansin, #470): each Stage from its left side (+X) and isometric from its front left (+X, -Y, +Z),
  orthographic, every panel at one scale on one ground line, framed tight to the largest silhouette (pictures.py
  VIEWS, PANELS). The landing page and Pictures showed them in one grid until #640 (macros.py panels): a column per Stage, a row
  per view, each linking to its file; on a phone stacked by Stage.
- The site's icon (#603; until #640, now Yellow Pine's pine): Stage 1's right eye at rest from straight ahead (its eyeball, pupil and lids alone,
  orthographic, square), rendered with the panels in the same look and served as a PNG (pictures.py FAVICON). A PR
  renders it with its preview panel.
- README media (#117), never in git (#226: `just pictures`, the motions packable into runners (`just blender-bins`,
  #297, #496), model/render/pictures.py SITE, a PR's preview panel and the next Mech's, pictures.py PREVIEW, #562, #629; the hero in frame shards
  of about a minute each, model/shards.py, #537; until #640 CI rendered them and the site served them): the hero, an animated WebP (`just hero`: stage 3 from 15 degrees to its right, 15
  degrees above, perspective; an 8 s talking loop keyed by hand in model/render/hero.py and played by MuJoCo (its
  trajectory), the head's pan and nod in
  head degrees through the four-bar kinematics (model/stages.py pose), every pose within geometry.LIMITS and free of
  penetrations as MuJoCo's report judges a sweep), the Stage panels, no photos. The gestures played in the web viewer on
  the landing page and at /viewer (#468), and Stage 3 exploded there (#482), until #640.
- Real photos of the build are local only (docs/references/build-photos, gitignored): ground truth for the model, never in git, the README or the site (Cansin, 2026-11-01: no staged photos yet).

## Numbers from the code

The picture sizes and the colours, as model/render/pictures.py and blender.py, model/geometry.py SPOOLS and
model/mjcf.py VIEW set them.

<!--{{ pictures }}-->

<!--{# GitHub shows the line below; the site drops it for the tables above, which it builds from the code -->
They are in [the tables on the site](https://yellowpine.com/noggin/docs/model-notes/#numbers-from-the-code).
<!-- #}-->

## Our printed parts (#50)
- Every printed part gets an independent parametric CadQuery design in model/printed/: interfaces exact, in the
  designer's frame, registered in `model/printed/__init__.py` PARTS by our part name (GLOSSARY.md), with the
  features it declares for the mating check (its features(), in FEATURES).
- Each part has a test beside it probing the solid at the measured interfaces (holes, pins, pivots, mount faces) and
  its envelope; model/test_mating.py checks that our mesh carries every declared feature.

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
  at 40 deg or more, the stock pan and jaw bars excepted with their reasons (model/test_report.py KNOWN_TRANSMISSION).
- Every pair of parts certified clear at every step of each gesture and the hero, not only at the 100 ms frames:
  `mj_geomDistance` at the ends of a span, halved where the parts could move further than that (model/gates.py certify,
  model/test_trajectories.py). The next Mech's lid drives are certified the same way, reading the exact solids (#655).

## Our model is the source (#88, #97)
- Since `stock-parity` nothing reads docs/references: no gate against the designer's meshes, no vendor STEP meshing,
  no guide sheets. The designer's and the vendor's files are credits ([Credits](credits.md)) and history (docs/research) only.
- Every picture (`just render`, `just hero`) draws our geometry, never the designer's meshes (Cansin, 2026-10-31).
- `just stl` (#98): our printed parts as print-ready STLs (mm, the designer's frames, 0.02 mm tessellation) in
  model/build/stl; future prints use ours.
- `just step` (#98): every part and envelope, and each Stage at neutral (model/stages.py's placements, coloured, one
  assembly), as STEP files in model/build/step; `open -a FreeCAD model/build/step/noggin-stage3.step`.

## Planned edits (notes only, never in the model; #81)
Today's documents follow Cansin's build, then our model (CLAUDE.md). What we plan to change in today's Mech stays here
until the model stabilises.
- The next Mech (#51; the spec lives there) is designed in the model instead, as its own documents beside the Stages
  (geometry.NEXT, #629), clean-room: none of today's printed parts or their dimensions, only the Envelopes of the
  hardware we own until its own parts land: linked eyes (one servo for left/right, one for up/down, each lid
  its own), a big head, the redesigned base (boards in the cranium, the pack in the shirt area), a black PETG skeleton (checked
  as PETG HF, geometry.MATERIALS' worst case, until the spool's variant is confirmed)
  with magnet-mounted PLA Pure character shells, Morty and Bart ([Skeleton and shells](face-design.md)).
  Its eye gimbal is in (#630, model/gimbal.py, the parts in model/printed/gimbal.py): drawn at rest in the next Mech's documents, moved
  by its own kinematics, its numbers in the next Mech's sim report under "gimbal" (gaze error with every pin's play and
  the pupil's seating, each term beside the total: a pupil keyed with 0.3 mm of seat play, #650; yaw/pitch crosstalk
  beside the Hooke form, the vergence a print error makes, the lids' clearance and range, the caps' gap, and the lid
  drives' sweep: each lid, bar, horn and shank against the frame and every other part, certified along every line of the
  lid x pitch grid at yaw 0 that turns the pair, #655; the pairs touching at rest checked for overlap at the grid's
  points), gated in model/test_report.py. The pitch push-rod's Hooke coupling is undone by the command map
  `gimbal.servos(yaw, pitch)`, which the noggin service applies once it drives the next Mech; every size is inferred.
  Its neck and jaw are in (#641, model/neck.py, the parts in model/printed/neck.py), drawn in the head's frame under the
  gimbal: the head turns on its own pivots (the yoke on the neck mount for pan, the head mount on the yoke's cheeks for
  tilt, straight under the head's centre of mass at rest, the jaw on the head mount's lugs), each servo drives through
  a bar, each busy pivot is a greased M3 shank turning in a Z-printed bore. Its numbers are in the next Mech's sim
  report under "neck" (each bar's transmission angle and servo range, the tilt servo's hold for the head the MJCF
  weighs, the flexing spans' bends), gated in model/test_report.py; every size is inferred. Since #642 it moves in
  MuJoCo (its horns named as today's Stages', so the sim report's neck figures, tip-over and the Core's servo names
  apply) and plays the next hero: the hero's head and jaw keys through its own four-bars (hero.next_at), the one
  motion that turns it, certified for clearance with the gestures (model/test_trajectories.py); the gimbal stays
  posed by its own kinematics.
- The Base candidates (#642, model/base.py, the parts in model/printed/base.py, GLOSSARY): one document each,
  next-mech-a and next-mech-b, both on one base plate with the pack lying behind the neck mount. (a) the boards on a
  tray screwed under the gimbal frame's plate behind the head mount, riding pan and tilt; (b) the boards on a shelf
  over the lids, on a PETG rod standing on the pan axis, the only line a static post can rise along in a head that
  pans, so it meets the neck's and the gimbal's middle (listed in model/test_report.py KNOWN_PAIRS for that reason).
  Each one's parameters are optimised in MuJoCo (model/candidates.py, `python -m model.candidates`; a model test holds
  the drawn numbers to it): (a)'s tray place for the tilt servo's least worst hold, kept clear of the yoke and the
  pack; (b)'s rod radius, the thinnest that sways at 8 Hz. `just sim` ranks them from their reports into
  model/build/reports/next-mech-ranking.json (base.rank: the clearance gate, #51's marks, then its criteria in order).
  Every size is inferred; Cansin picks.
- From the #81 sweep, the remaining non-original choices in the model (each marked inferred where it is used; the
  values that waited for a measurement are settled as best guesses, docs/research/2026-11-01-best-guesses.md):
  - the horns' spline tooth at servo 90 (geometry.HORN_AT_90): lids by the calibrated closed end (lo 39), its edges just touching (#134, #189, #255), eyes +2 from the
    program's eye centre (#170); the lid crank's 1.2 mm play along its screw (geometry.CRANK_PLAY_MM, #170); the lids'
    open ends still collide in the model and were accepted with their reason (#170, #189) until #151 dropped the
    exact-mesh check that measured the calibrated ends; since #255 the gestures' wide lids (eureka) are judged per frame
    and listed with that reason (model/test_trajectories.py KNOWN_CALIBRATED);
  - every cable corridor waypoint (read off the build and guide photos, placed by eye), the servo lead length (250 mm,
    the typical 9 g figure; the vendor publishes none) and the Y lead's branches (100 mm each);
  - the bracket stem's depth in the plate's slot (stage 1, from the build photos) and in the tilt arm window (stages 2, 3)
    (geometry.STEM_AT);
  - the receiver headers' PWM numbering (geometry.RECEIVER_STEP; no numbering changes a result);
  - the jaw bar seated flush between the jaw lug and the horn arm (geometry.PT_BAR_PLANES, #170);
  - the horn limits, each with its reason (geometry.LIMITS);
  - masses of the boards, battery and horn from STEP volume x 1.9 g/cm3; two spool colours (wire holder, pan turntable);
  - the lid horns keep the STEP horn's r 0.5 hole in the mesh, though they are drilled to r 1.0 (axis unchanged).
- Conflict, settled (#172): the eyes on the desk base. Cansin's side photo has the servo brackets' feet on the plate
  top, and the model kept that while the rail bracket's rail lay 5 mm in the plate and its stem sat on the pan boss. The
  build was right: the desk build uses the designer's first bracket (no rail, geometry.DESK) with its stem in the
  plate's 12 x 5 slot (docs/research/2026-11-01-eyes-on-plate.md).
