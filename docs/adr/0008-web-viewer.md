# The web viewer draws Blender's glTF in three.js on GitHub Pages

> Decided with Cansin on 2026-11-01, spec #180; tickets #181 (the page and the Pages workflow) and #182 (the GLBs).
> Follows ADR 0007: MuJoCo simulates, Blender draws, and now Blender also authors what the browser shows.
> Amended 2026-11-01 (#194): three.js replaces `<model-viewer>` so the page shows style B, the pictures' look.

The README's stills and GIFs show the Mech from fixed angles. The web viewer is a public page on GitHub Pages
(yellow-pine.github.io/noggin, linked from the README) where anyone can orbit and zoom a Stage, play each gesture and
watch the hero loop.

- **Baked, not simulated, in the browser.** Motion is MuJoCo's baked servo trajectories (#179), the same source as the
  GIFs and the hero. Blender keys every part's world pose per frame and exports one Draco-compressed GLB per Stage,
  with one named glTF animation per gesture plus `hero` (actions stashed so the exporter includes each).
- **three.js draws it in style B** (MIT, one pinned version from the CDN, a sha384 hash per file in the import map):
  `MeshToonMaterial` whose gradient map is the pictures' light per N.L (the two-step toon ramp mixed with the satin,
  sampled from Blender's numbers) and one highlight band, black outlines on silhouettes (an inverted hull)
  and crease lines where faces meet at more than 60 degrees, the key light riding at the camera's upper right.
  Orbit and zoom are `OrbitControls`, gestures and the hero play through `AnimationMixer`, the Stage switch loads the
  other GLB. The page is one static HTML file in `web/`, with no build step. three.js's Draco decoder is fetched by
  `DRACOLoader` with no integrity check, so the site serves its own copy, sha256-checked when the site is built.
- **One source for the look.** Blender's export writes the look numbers (background, line width, crease angle, the
  light ramp, highlight, key light) into the GLB scene's glTF extras and each part's colour into its glTF material; the
  page reads them and holds no look numbers of its own.
- **Built in CI, deployed with GitHub's own Pages actions.** A Pages workflow runs on a push to main that touches
  `model/`, `eyes/` or `web/`, and on demand. It is not a required check: a red build leaves the last site up and
  blocks no PR. Pages' source is GitHub Actions, so nothing built is committed. It bakes the trajectories and runs
  the pinned Blender 5.2.2 Linux tarball (sha256-checked, cached).
- **Eyes gestures only for now.** Head and jaw gestures come with the second Core; Stages 2 and 3 show the eyes
  gestures and the hero loop.

## Considered options

- Live MuJoCo in the browser (the WASM build): rejected, physics per viewer for motion that is already baked, and a
  second look beside Blender's.
- Google's `<model-viewer>` (the first page, #181): rejected in #194. It covers orbit, zoom and named animations with
  no code, but it draws glTF's PBR materials only: no toon ramp, no outlines, no crease lines, so the page did not
  look like the GIFs. Freestyle lines and Eevee's Shader-to-RGB ramp have no glTF form.
- three.js's `OutlineEffect` for the silhouettes: rejected, it pushes along a unit normal in model units and our
  GLBs are in metres (docs/research/2026-11-01-web-toon.md).
- Committing the GLBs (or deploying from a branch): rejected, binaries in history on every model change.
