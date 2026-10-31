# Model notes (Fusion documents of the Mech)

Decisions that are not in the code. Vocabulary: GLOSSARY.md (Model section); structure: docs/adr/0004.

## Rendering rules (2026-10-31)
- Parts carry their real spool's appearance (Bambu PLA Pure: Milky Pink #F7CED7, Pure White #FFFFFF, Absolute
  Black #000000, Apricot #FFB673) and a "Bambu PLA Pure" physical material (1.24 g/cm3); the table is data in
  model/geometry.py. Electronics and servos keep their STEP appearances.
- Screenshots use plain shading, no mesh edges, and hide joint glyphs, sketches, construction geometry and
  origins for the capture (fusion_lib.screenshot). Each view is saved twice: `<stage>-<view>.png`
  clean and `<stage>-<view>-overlay.png` with the reference-photo canvases shown.
- Reference-photo canvases sit at 25 % opacity and are hidden by default in the saved document (shown only while
  the overlay screenshots are captured); `make model-canvases` toggles them in the active document.
- Views: top (looking down -Y, up +Z), side (looking +X, up +Y), front (looking +Z, up +Y) of the eyes frame.
- Canvases only for the eyes Stage (80/20 trim); later Stages get the three plain views.
- README media are Fusion renders and replay GIFs only (coloured parts, no photo canvases); real photos stay in
  docs/build-photos for the model comparison.
- Gesture replay (`python model/traces.py`, issue #39): noggin-stage1 (base + eyes, as on the desk), the eyes' link
  broken in memory and the document closed unsaved. README view: perspective camera from the viewer's front-left
  (the mech's right) at 45 degrees, 25 degrees above the eye centre line, aimed between the eyes and the base middle
  (model/replay.py VIEW, AIM), into model/build/replay/<gesture>/, GIFs 480 wide, 10 fps, 128 colours, under 1 MB.
  The straight front view (orthographic) goes to model/build/replay/<gesture>-front/ for symmetry checks, not in the
  README. Joints move in steps of at most 4 degrees between frames: larger jumps can flip Fusion's lid four-bars onto
  their other branch. Lids map the eye program's fraction onto the model's own closed/open horn angles
  (model/engine/lids.py), never servo degrees.
