# Model notes

Decisions that are not in the code. Vocabulary: GLOSSARY.md (Model section); structure: docs/adr/0004.

## Rendering rules (2026-10-31, #47)
- Fusion only builds documents: no screenshots, no reference-photo canvases or overlay views. Every picture is
  rendered in Blender (headless, Eevee) from the poses the Python engine computes (model/engine): `make render`
  for the views, `make gifs` for the gestures; code in model/render, output in model/build/pictures.
- Parts carry their real spool's colour (Bambu PLA Pure: Milky Pink #F7CED7, Pure White #FFFFFF, Absolute Black
  #000000, drawn #2B2B2E so its shading and lines read, Apricot #FFB673; data in model/geometry.py SPOOLS/PRINTED)
  and a "Bambu PLA Pure" physical material (1.24 g/cm3) in Fusion. Electronics and servos are neutral greys,
  darker for the boards (model/render/scene.py GREYS).
- Look (Cansin's pick, style B): satin plastic (roughness 0.45, low specular) mixed 45/55 with a two-step toon
  shadow and one small highlight band, 2.5 px black Freestyle lines on silhouettes, borders and creases (faces
  more than 60 degrees apart, so STL facets draw none), one key light at the camera's upper right, plain #F7F4EE
  background. STL facets are smoothed by angle (35 degrees) with weighted normals; pupils are lifted 0.3 mm off the
  eyeball so their outline stays whole.
- Views, orthographic, 1600x1200, fitted to the parts: top/side/front of each sub-assembly (base, stack, eyes, the
  mouth on the eyes) and each Stage (as Fusion's views: PT frame top looking down Z, side from +X, front from -Y; eyes
  frame top from +Y, side from -X, front from -Z).
- README media: the hero (stage 3 from the front, 10 degrees above, perspective), the Stage strip (stage 1 front,
  stage 2 side, stage 3 side and front at one scale on one ground line) and the gesture GIFs.
- Gesture GIFs: noggin-stage1, perspective from the Mech's front-right (right eye nearest) 25 degrees above, framed
  on the eyes with the base's front in view; one frame per 100 ms of the Core program's own commands mapped onto the
  model's joints (model/traces.py: lid fractions onto the model's closed/open angles, model/engine/lids.py; never
  servo degrees), rendered 600x450 and encoded 480 wide, 10 fps, 64 colours, at most 1 MB each, with a contact sheet per gesture.
- Real photos stay in docs/build-photos for the model comparison, never in the README model media.

## Our printed parts (#50)
- Every printed part gets an independent parametric CadQuery design in model/printed/ (never traced from the
  designer's mesh, which stays local under docs/references): interfaces exact, envelope within 1 mm, in the designer's
  frame, registered in `model/printed/__init__.py` PARTS by the STL stem it stands in for.
- Each part has a test beside it probing the solid at the measured interfaces (holes, pins, pivots, mount faces) and
  its envelope; `model/printed/test_gate.py` swaps it for the designer's mesh in every document that places it and
  requires identical transmission and every clearance within 0.3 mm (local only: skipped without docs/references).
