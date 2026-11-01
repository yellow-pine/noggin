# The web viewer draws Blender's glTF in three.js on GitHub Pages

> Decided with Cansin on 2026-11-01, spec #180; tickets #181 (the page and the Pages workflow) and #182 (the GLBs).
> Follows ADR 0007: MuJoCo simulates, Blender draws, and now Blender also authors what the browser shows.
> Amended 2026-11-01 (#194): three.js replaces `<model-viewer>` so the page shows style B, the pictures' look.
> Amended 2026-11-01 (#211): the key light casts shadows, lines scale with the canvas.
> Amended 2026-11-01 (#225, ADR 0009): the viewer moved to yellowpine.com/noggin/viewer/, the site's docs took the root.
> Amended 2026-11-01 (#221): a PR touching `model/`, `eyes/` or `web/` bakes and tests the GLBs too; every run reuses
> the last GLBs built from the same inputs.
> Amended 2026-11-01 (#268): the site serves three.js itself; the page runs scripts from the site alone.
> Amended 2026-11-01 (#271): the camera frames the Stage as the hero GIF does, and lines follow its size on screen.
> Amended 2026-11-01 (#281): the viewer is a page of the docs site at /viewer/, in its theme (header, search, nav);
> docs pages can drop in a small one per Stage.

The README's stills and GIFs show the Mech from fixed angles. The web viewer is a public page on GitHub Pages
(yellow-pine.github.io/noggin, linked from the README) where anyone can orbit and zoom a Stage, play each gesture and
watch the hero loop.

- **Baked, not simulated, in the browser.** Motion is MuJoCo's baked servo trajectories (#179), the same source as the
  GIFs and the hero. Blender keys every part's world pose per frame and exports one Draco-compressed GLB per Stage,
  with one named glTF animation per gesture plus `hero` (actions stashed so the exporter includes each).
- **three.js draws it in style B** (MIT, one pinned version, served by the site; see the last paragraph of this bullet):
  `MeshToonMaterial` whose gradient map is the pictures' light per N.L (the two-step toon ramp mixed with the satin,
  sampled from Blender's numbers) and one highlight band, black outlines on silhouettes (an inverted hull)
  and crease lines where faces meet at more than 60 degrees, the key light riding at the camera's upper right and
  casting shadows as Eevee's sun does (#211 measured the pictures' two tones to be these cast shadows). On load and on a Stage switch the camera
  frames the Stage as the hero GIF does (its view, 15 degrees to the right and up, every vertex in frame with the
  pictures' 1.06 margin). Lines follow the Stage's size on screen as the GIFs' do: `line_px` when it is as big as in a
  4:3 frame `line_at` (640) px wide, through every zoom and resize, never under 1 px nor over twice `line_px`.
  Orbit and zoom are `OrbitControls`, gestures and the hero play through `AnimationMixer`, the Stage switch loads the
  other GLB. The viewer is one module, `web/viewer.mjs`, and its framing module (`frame.mjs`, tested
  with `node --test`), with no build step of its own. It draws every `<div class="noggin-viewer" data-stage="stage1">`
  on a page, with a button per clip under it: the viewer's page (`web/viewer.md`, which a MkDocs hook puts at /viewer/
  in the theme's `viewer.html`: full width, no sidebars) adds the Stage buttons, and any docs page can drop in a small
  one. The theme (`overrides/main.html`) loads the module, the import map and the viewer's CSP on the pages that have
  one, Material's buttons style the controls, and a browser test (Playwright in Chrome, `web/test_viewer.py`) plays a
  gesture on the built site with no request to another host but GitHub's repo facts in Material's header.
  three.js, the addons it
  imports and the Draco decoder `DRACOLoader` fetches are copied into the site from the npm package when the viewer
  is built, each checked against its sha384 in `web/build.py` (`vendored.py`, as the docs' Mermaid is), and the import
  map points at those copies. The page's CSP lets scripts from the site alone run (plus the decoder's WASM in
  `DRACOLoader`'s Blob worker), so a missing copy fails instead of falling back to a CDN.
- **One source for the look.** Blender's export writes the look numbers (background, line width, crease angle, the
  light ramp, highlight, key light) into the GLB scene's glTF extras and each part's colour into its glTF material; the
  page reads them and holds no look numbers of its own.
- **Built in CI, deployed with GitHub's own Pages actions.** A Pages workflow runs on a push to main that touches
  `model/`, `eyes/` or `web/`, and on demand. A red build on main leaves the last site up; on a PR
  touching what the site is made from it fails the required `site` check (#245). Pages' source is GitHub Actions, so nothing built is committed. It bakes the trajectories and runs
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
