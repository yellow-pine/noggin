# The web viewer shows Blender's glTF in model-viewer on GitHub Pages

> Decided with Cansin on 2026-11-01, spec #180; tickets #181 (the page and the Pages workflow) and #182 (the GLBs).
> Follows ADR 0007: MuJoCo simulates, Blender draws, and now Blender also authors what the browser shows.

The README's stills and GIFs show the Mech from fixed angles. The web viewer is a public page on GitHub Pages
(yellow-pine.github.io/noggin, linked from the README) where anyone can orbit and zoom a Stage, play each gesture and
watch the hero loop.

- **Baked, not simulated, in the browser.** Motion is MuJoCo's baked servo trajectories (#179), the same source as the
  GIFs and the hero. Blender keys every part's world pose per frame and exports one Draco-compressed GLB per Stage,
  with one named glTF animation per gesture plus `hero` (actions stashed so the exporter includes each).
- **Google's `<model-viewer>` only displays it** (Apache-2.0, one pinned version from the CDN): orbit and zoom are its
  `camera-controls`, a gesture button sets `animation-name` and plays once, the Stage switch swaps `src`. The page is
  one static HTML file in `web/`, with no build step and no code of ours that draws.
- **Built in CI, deployed with GitHub's own Pages actions.** A Pages workflow runs on a push to main that touches
  `model/`, `eyes/` or `web/`, and on demand. It is not a required check: a red build leaves the last site up and
  blocks no PR. Pages' source is GitHub Actions, so nothing built is committed. It bakes the trajectories and runs
  the pinned Blender 5.2.2 Linux tarball (sha256-checked, cached).
- **Eyes gestures only for now.** Head and jaw gestures come with the second Core; Stages 2 and 3 show the eyes
  gestures and the hero loop.

## Considered options

- Live MuJoCo in the browser (the WASM build): rejected, physics per viewer for motion that is already baked, and a
  second look beside Blender's.
- A three.js viewer of our own: rejected, `<model-viewer>` covers orbit, zoom and named animations with no code.
- Committing the GLBs (or deploying from a branch): rejected, binaries in history on every model change.
