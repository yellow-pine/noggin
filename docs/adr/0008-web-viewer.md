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
> Amended 2026-11-01 (#333, ADR 0013): the page is an Astro page (`site/src/pages/viewer.astro`) and the module lives
> beside it in `site/src/viewer/`, loaded by the site's footer on any page with a viewer; Vite bundles three.js and its addons from npm, the Draco decoder is copied from
> three's package, and vendored.py, the import map and the page's own CSP are gone (the site's one CSP covers it).
> Amended 2026-11-02 (#468, spec #467): the landing page opens with a viewer of Stage 3, the hero GIF its poster until it
> loads (on scroll into view; on a phone on a "Play in 3D" tap), and the gesture GIFs are gone: the viewer's buttons
> are the one gesture picker, and each click keeps the address the deep link, `/viewer/?stage=<n>&gesture=<g>`.
> Amended 2026-11-02 (#482, spec #467): an Explode button moves Stage 3's sub-assemblies apart and back by the
> offsets the exploded render used (model/render/pictures.py EXPLODE, through macros.json), and `&explode=1` opens it so;
> the exploded render is gone.
> Amended 2026-11-02 (#482): the controls are one bar under the viewer: Stage a segmented 1 · 2 · 3, the gestures
> Title Case chips with the Tour (every clip in turn) in place of hero, and Explode a toggle; under it one line says
> what the gesture is and which Claude Code event plays it, from the behaviour table's code (macros.json). Deep links
> are unchanged.
> Amended 2026-11-02 (#538, #496): the viewer is built in the Checks workflow's `Blender` jobs, and a red build fails
> its required `Checks` gate, not a `site` check.
> Amended 2026-11-02 (#547): "Built in CI" describes the Checks workflow and Site Deploy, not the Pages workflow.
> Amended 2026-11-02 (#640, ADR 0019): the viewer is off the site and CI bakes no GLB until the clean-room Mech;
> `just web` bakes them locally.
> Amended 2026-11-02 (#649, ADR 0019): the viewer is back on the site at /viewer/ for the Next Mech alone
> (`next-mech.glb`, baked by Checks' `Blender` job); it is still, so its GLB has no clips and the page no gesture bar.
> Amended 2026-11-02 (#642): a GLB per Base candidate (`next-mech-a.glb`, `next-mech-b.glb`), one viewer each.
> Amended 2026-11-02 (#686): a GLB per head variant (`next-mech-back.glb`, `-crown`, `-split`) in their place, its
> button in the ranking's order, marked with what it fails.

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
  other GLB. The viewer is one module, `site/src/viewer/viewer.mjs`, its framing module (`frame.mjs`) and its deep
  link, caption and explode offsets (`state.mjs`), both tested with Vitest, bundled by the site's build. It draws
  every `<div class="noggin-viewer" data-stage="stage1">` on a page, with a button per clip under it: the viewer's
  page (`site/src/pages/viewer.astro`, in Starlight's theme with no table of contents) adds the Stage buttons, and
  any page can drop in a small one. A browser test (Playwright in Chrome, `site/smoke.pw.mjs`) loads Stage 1 on the
  built site with no error and no request to another host but GitHub's repo facts in the header. three.js and its
  addons come from npm, bundled by the site's build, and the Draco decoder `DRACOLoader` fetches is copied from the
  same package; the lockfile's integrity hashes pin them (ADR 0013). The site's CSP lets scripts from the site alone
  run (plus the decoder's WASM in `DRACOLoader`'s Blob worker).
- **One source for the look.** Blender's export writes the look numbers (line width, crease angle, the light ramp,
  highlight, key light) into the GLB scene's glTF extras and each part's colour into its glTF material; the page reads
  them and holds no look numbers of its own. The canvas is see-through: the background is the page's own, in either theme.
- **Built in CI, deployed with GitHub's own Pages actions.** The Checks workflow (`checks.yml`) builds the viewer on
  PRs and on main: a `Blender` job bakes the trajectories and runs `just web` in our Blender image, which holds the
  pinned Blender Linux tarball (sha256-checked; re-pinned weekly by `blender.yml`), when what the viewer is made from
  changed (`scripts/inputs.py`), else the gate restores the last viewer built from the same inputs. The `Checks` gate
  puts it in the site and plays it in Chrome, and a red build fails that required gate (#245, #496). Site Deploy
  (`pages.yml`) deploys main's site artifact once main's Checks passed, with no rebuild; a red build on main leaves
  the last site up. Pages' source is GitHub Actions, so nothing built is committed.
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
