# Model notes

Decisions that are not in the code. Vocabulary: GLOSSARY.md (Model section); structure: docs/adr/0004.

## Rendering rules (2026-10-31, #47)
- No screenshots, reference-photo canvases or overlay views: every picture is rendered in Blender (headless, Eevee)
  from the poses the Python engine computes (model/engine): `make render` for the views, `make gifs` for the gestures;
  code in model/render, output in model/build/pictures.
- Parts carry their real spool's colour (Bambu PLA Pure: Milky Pink #F7CED7, Pure White #FFFFFF, Absolute Black
  #000000, drawn #2B2B2E so its shading and lines read, Apricot #FFB673; data in model/geometry.py SPOOLS/PRINTED)
  and the Bambu PLA Pure density (1.24 g/cm3). Electronics and servos are neutral greys,
  darker for the boards (model/render/scene.py GREYS).
- Look (Cansin's pick, style B): satin plastic (roughness 0.45, low specular) mixed 45/55 with a two-step toon
  shadow and one small highlight band, 2.5 px black Freestyle lines on silhouettes, borders and creases (faces
  more than 60 degrees apart, so STL facets draw none), one key light at the camera's upper right, plain #F7F4EE
  background. STL facets are smoothed by angle (35 degrees) with weighted normals; pupils are lifted 0.3 mm off the
  eyeball so their outline stays whole.
- Views, orthographic, 1600x1200, fitted to the parts: top/side/front of each sub-assembly (base, stack, eyes, the
  mouth on the eyes) and each Stage (PT frame top looking down Z, side from +X, front from -Y; eyes
  frame top from +Y, side from -X, front from -Z).
- README media: the hero (stage 3 from the front, 10 degrees above, perspective), the Stage strip (stage 1 front,
  stage 2 side, stage 3 side and front at one scale on one ground line) and the gesture GIFs.
- Gesture GIFs: noggin-stage1, perspective from the Mech's front-right (right eye nearest) 25 degrees above, framed
  on the eyes with the base's front in view; one frame per 100 ms of the Core program's own commands mapped onto the
  model's joints (model/traces.py: lid fractions onto the model's closed/open angles, model/engine/lids.py; never
  servo degrees), rendered 600x450 and encoded 480 wide, 10 fps, 64 colours, at most 1 MB each, with a contact sheet per gesture.
- Real photos stay in docs/build-photos for the model comparison, never in the README model media.
- Guide sheets (#68, `make guide-sheets`): each step of PurpleShark's three guides (model/render/guide.py STEPS: page,
  picture, parts, camera matched by eye) as a row of guide page, guide picture and the model with only that step's parts,
  one sheet per guide in model/build/pictures/guide. Visual output, never committed; the PR records which steps match.

## Our printed parts (#50)
- Every printed part gets an independent parametric CadQuery design in model/printed/ (never traced from the
  designer's mesh, which stays local under docs/references): interfaces exact, envelope within 1 mm, in the designer's
  frame, registered in `model/printed/__init__.py` PARTS by the STL stem it stands in for.
- Each part has a test beside it probing the solid at the measured interfaces (holes, pins, pivots, mount faces) and
  its envelope; `model/printed/test_gate.py` swaps it for the designer's mesh in every document that places it and
  requires identical transmission and every clearance within 0.3 mm (local only: skipped without docs/references).

## Our hardware envelopes and CI (#58)
- The Bambu STEPs (servo, horn, Shield, Core, switch board, battery) stay local too: model/envelopes.py draws a simple
  CadQuery envelope of each in its STEP frame, with the interfaces (tab holes, shaft, mount holes, connectors) at the
  STEP's numbers (model/test_envelopes.py); the gate holds them to the tessellated STEPs like the printed parts.
- `make ours` (model/ours.py) writes every printed part and envelope to model/build/ours as STLs, in its own process
  (CadQuery's threads must not precede the sweep's fork). Without docs/references the engine reads those
  (model/engine/stages.py HAVE_REFERENCES): CI runs `make check` and then `make sim` on our geometry alone. Locally
  `make sim` keeps the designer's meshes and STEPs, so the committed reports are theirs, and the gate checks ours
  against them.
- Every picture (`make render`, `make gifs`) draws our geometry, never the designer's meshes (Cansin, 2026-10-31).

## Planned edits (notes only, never in the model; #81)
The model follows Cansin's build, then PurpleShark's stock version (CLAUDE.md). What we plan to change stays here until
the model stabilises.
- One pack and one switch board per shield (CLAUDE.md, ADR 0005), instead of stock's one pack and a Y lead to both: the
  one pack's worst case (every servo at stall, both shields, a Wi-Fi burst each) is 5.34 A against its 3 A continuous
  (model/electrical.py `pack_a`); each shield alone stays under 3 A. Needs a second battery box and switch holder.
- The cranium layout (#51): flat base, a static board tower, or boards riding in the head; batteries stay low.
- From the #81 sweep, the remaining non-original choices in the model (each marked inferred where it is used):
  - the horns' spline tooth at servo 90: the model takes the STL pose; the rest photo does not settle it
    (docs/research/2026-10-31-shafts.md), so the calibrated-end collisions stay listed (model/test_report.py);
  - every cable corridor waypoint (read off the build and guide photos, placed by eye), the servo lead length (250 mm,
    not published) and the Y lead's branches (100 mm each);
  - the bracket stem's depth in the pan recess (stage 1) and in the tilt arm window (stages 2, 3) (geometry.STEM_AT);
  - the receiver headers' PWM numbering (geometry.RECEIVER_STEP);
  - the jaw horn pin's 0.58 mm bar/arm overlap (model/engine/mating.py INFERRED);
  - the model limits where the model collides before the designer's ends (geometry.MODEL_LIMITS, each with its reason);
  - masses of the boards, battery and horn from STEP volume x 1.9 g/cm3; two spool colours (wire holder, pan base);
  - the lid horns keep the STEP horn's r 0.5 hole in the mesh, though they are drilled to r 1.0 (axis unchanged).
