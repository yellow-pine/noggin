# Model notes

Decisions that are not in the code. Vocabulary: GLOSSARY.md (Model section); structure: docs/adr/0004.

## Rendering rules (2026-10-31, #47)
- No screenshots, reference-photo canvases or overlay views: every picture is rendered in Blender (headless, Eevee)
  posed from MuJoCo's baked trajectories (model/trajectories.py `poses`, `make trajectories`; #150): `make render` for
  the views (each Stage at rest, a trajectory's first frame; sub-assemblies at their placement), `make gifs` for the
  gestures; code in model/render, output in model/build/pictures.
- Parts carry their real spool's colour (PLA: model/geometry.py SPOOLS/PRINTED, under Numbers from the code below; Absolute Black
  drawn a touch lighter so its shading and lines read) and the PLA density (1.24 g/cm3). Electronics and servos are
  neutral greys, darker for the boards (model/render/scene.py GREYS).
- `make view` (MuJoCo's viewer, local checks only; Cansin kept it 2026-11-01, model/test_mjcf.py pins it and CI
  renders it offscreen): headlight ambient 0.5, diffuse 0.5, specular 0; Absolute Black and Pure White pulled in
  (model/mjcf.py VIEW), the rest their spool's colour; a flat sky in the pictures' background. Added in #150, merged on green: a directional key
  light from the Mech's upper front-left casting shadows (diffuse and specular 0.3) and satin parts (specular 0.3,
  shininess 0.5).
- Look (Cansin's pick, style B): satin plastic (roughness 0.45, low specular) mixed 45/55 with a two-step toon
  shadow and one small highlight band, black lines on silhouettes and creases (faces more than 60 degrees apart, so
  STL facets draw none; their width blender.py ART_PX in the pictures, LINE_PX in the web viewer), one key light at the camera's upper right, a plain background. STL facets are
  smoothed by angle (35 degrees) with weighted normals; pupils are lifted 0.3 mm off the eyeball so their outline stays
  whole. For CI's software GL (Cansin, 2026-11-01, #226, #276; docs/research/2026-11-01-render-profile.md): Blender's
  Line Art draws the lines (Freestyle took ~90 % of a frame on one thread), Eevee takes 4 samples a frame (was 64), the
  GIFs render at the size they ship, 8 fps, keeping toon timing's key frames (pictures.py at_fps).
- Views, orthographic, fitted to the parts: top/side/front of each sub-assembly (base, stack, eyes, the
  mouth on the eyes) and each Stage (PT frame top looking down Z, side from +X, front from -Y; eyes
  frame top from +Y, side from -X, front from -Z).
- README media (#117), built in CI and served from the site, never in git (#226: `make pictures`, the pages
  workflow's `pictures` job, views, gifs and hero each on its own runner; model/render/pictures.py SITE;
  yellowpine.com/noggin/images/): the hero GIF (`make hero`: stage 3 from 15 degrees to its right, 15
  degrees above, perspective; an 8 s talking loop keyed by hand in model/render/hero.py and played by MuJoCo (its
  trajectory), the head's pan and nod in
  head degrees through the four-bar kinematics (model/stages.py pose), every pose within geometry.LIMITS and free of
  penetrations as MuJoCo's report judges a sweep), the Stage strip
  (stage 1 front, stage 2 side, stage 3 side and front at one scale on one ground line), stage 3 exploded (same
  camera direction as the hero) and the six gesture GIFs: about 6 MB in all, no photos.
- Gesture GIFs: noggin-stage1, perspective from the Mech's front-right (right eye nearest) 25 degrees above, framed
  on the eyes with the base's front in view; one frame per 100 ms of the gesture's trajectory (MuJoCo playing the Core
  program's own writes through the servos' dynamics: model/traces.py `commands`, lid fractions through
  eyes/calibration.json to the shared lid frame's degrees, plus the lid horns' spline tooth, geometry.HORN_AT_90), with
  a contact sheet per gesture; their sizes are under Numbers from the code below.
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
- `make ours` (model/ours.py) writes every printed part and envelope to model/build/ours as STLs, in its own process
  (CadQuery's threads must not precede a process pool's fork). The model always reads those: `make test` and `make sim`
  build them first, and the reports are simulated on our geometry; CI builds them (never committed) and the site
  publishes main's at /reports (docs/adr/0009).

## Our model is the source (#88, #97)
- Since `stock-parity` nothing reads docs/references: no gate against the designer's meshes, no vendor STEP meshing,
  no guide sheets. The designer's and the vendor's files are credits ([Credits](credits.md)) and history (docs/research) only.
- Every picture (`make render`, `make gifs`) draws our geometry, never the designer's meshes (Cansin, 2026-10-31).
- `make stl` (#98): our printed parts as print-ready STLs (mm, the designer's frames, 0.02 mm tessellation) in
  model/build/stl; future prints use ours.
- `make step` (#98): every part and envelope, and each Stage at neutral (model/stages.py's placements, coloured, one
  assembly), as STEP files in model/build/step; `open -a FreeCAD model/build/step/noggin-stage3.step`.

## Planned edits (notes only, never in the model; #81)
The model follows Cansin's build, then our model (CLAUDE.md). What we plan to change stays here until
the model stabilises.
- One pack and one switch board per shield (CLAUDE.md, ADR 0005), instead of stock's one pack and a Y lead to both: the
  one pack's worst case (every servo at stall, both shields, a Wi-Fi burst each) is 5.34 A against its 3 A continuous
  (model/electrical.py `pack_a`); each shield alone stays under 3 A. At the pack's 5.8 V cutoff the servos sag to
  3.6 V at stall (`servo_v`, below their 4.8 V minimum); the Cores hold 3.3 V. Needs a second battery box and switch holder.
- The cranium layout (#51): flat base, a static board tower, or boards riding in the head; batteries stay low.
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
