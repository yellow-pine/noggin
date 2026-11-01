# Web viewer: model-viewer, the Pages actions and the Blender tarball (2026-11-01, #181)

Question: what to pin for the static Pages viewer (#180, #181): which `<model-viewer>` build, how its animation API
behaves for "play one gesture once" and "loop the hero" across a Stage `src` swap, the official Pages actions by
commit SHA, and the Blender 5.2.2 Linux tarball with its sha256. Rule: newest release at least two weeks old.

Sources: model-viewer source at tag v4.4.0 (`MV/` = https://github.com/google/model-viewer/blob/v4.4.0/packages/model-viewer/src/),
its API reference (https://modelviewer.dev/docs/, generated from
https://github.com/google/model-viewer/blob/v4.4.0/packages/modelviewer.dev/data/docs.json), the npm registry, the
GitHub API, docs.github.com and download.blender.org, all read 2026-11-01.

## model-viewer: pin 4.4.0

- npm `latest` is 4.4.0, published 2026-10-09T20:10:31Z (23 days old); before it 4.3.1 (2026-06-04)
  (`npm view @google/model-viewer time`, https://registry.npmjs.org/@google/model-viewer). GitHub release v4.4.0 is the
  latest (https://github.com/google/model-viewer/releases/tag/v4.4.0).
- The README's CDN line is Google Hosted Libraries, `<script type="module" src=".../model-viewer.min.js">`
  (https://github.com/google/model-viewer/blob/v4.4.0/packages/model-viewer/README.md#cdn); modelviewer.dev itself
  loads `https://ajax.googleapis.com/ajax/libs/model-viewer/4.4.0/model-viewer.min.js`. Both resolve (`curl -sI`, 200):
  that URL, and `https://cdn.jsdelivr.net/npm/@google/model-viewer@4.4.0/dist/model-viewer.min.js`
  (`x-jsd-version: 4.4.0`, `cache-control: immutable`).
- **4.4.0 is the floor for our gesture buttons.** Before it, setting `animationName` and then calling
  `play({repetitions: 1})` looped forever and never fired `finished`, because the async `animationName` update replayed
  with the infinite default. Fixed by PR #5179, merged 2026-06-16, after 4.3.1
  (https://github.com/google/model-viewer/pull/5179; the fix's comment is MV/features/animation.ts#L101-L106).
- `animation-name` / `animationName`: selects the clip by name, played on `play()` or autoplay; with none set it picks
  the first clip (docs). Lookup is exact name, else a numeric index, else clip 0 (MV/three-components/ModelScene.ts#L909-L931).
  Changing it while playing replays with the options of the last `play()` call (MV/features/animation.ts#L263-L274) and
  crossfades over `animation-crossfade-duration`, default 300 ms (#L96-L97).
- `autoplay`: plays when set, and on every model load (docs; MV/features/animation.ts#L229-L240, #L259-L261).
- `play({repetitions, pingpong})`: repetitions default Infinity, pingpong default false (docs; MV/features/animation.ts#L53-L56).
  `repetitions: 1` maps to three.js `LoopOnce` (#L274-L277), and the action holds its last frame
  (`clampWhenFinished = true`, MV/three-components/ModelScene.ts#L960). The options exist since v1.10.0 (absent from
  `animation.ts` at v1.9.0, present at v1.10.0). Replaying the same clip at its end rewinds to 0 (ModelScene.ts#L952-L955).
- `finished`: "Dispatched when the current animation has finished playing" (docs). It is the three.js mixer's
  `finished`, so it fires only for a finite play (LoopOnce or finite repetitions), never for the infinite hero loop; it
  also marks the element paused (MV/features/animation.ts#L132-L140). `loop` fires per loop with `e.detail.count` (#L112-L130).
- `availableAnimations`: clip names of the loaded model, `[]` until `loaded` (docs; MV/features/animation.ts#L147-L153).
- **On a `src` swap** (the Stage switch): `load` fires again, "can fire multiple times ... if the src attribute is
  changed" (docs). On load the scene is paused, the current `animationName` is re-applied (so the same name carries over;
  a name the new GLB lacks falls back to its first clip), and if `autoplay` is set, `play()` runs with **no options, i.e.
  repetitions Infinity** (MV/features/animation.ts#L229-L240). So: keep the hero as `autoplay` + `animation-name`, and
  after a gesture's `finished`, set `animationName` back to the hero and call `play()` (default options) to loop again.
- `camera-controls`: "Enables controls via mouse/touch" (orbit, zoom); should nearly always be set (docs).
- Draco: works out of the box. Every load goes through three.js `DRACOLoader` (MV/three-components/CachingGLTFLoader.ts#L65,
  #L162), and the decoder is lazy-loaded from `https://www.gstatic.com/draco/versioned/decoders/1.5.6/` unless the
  static `ModelViewerElement.dracoDecoderLocation` is set (MV/features/loading.ts#L29-L30, #L312-L314; docs: "By default,
  the DRACO decoder will be loaded from a Google CDN"). So the page fetches from gstatic at runtime too.

## GitHub Pages actions (latest releases, all lightweight tags pointing at the commit)

| Action | Tag | Published | Commit |
| --- | --- | --- | --- |
| actions/configure-pages | v6.0.0 | 2026-03-25 | `45bfe0192ca1faeb007ade9deae92b16b8254a0d` |
| actions/upload-pages-artifact | v5.0.0 | 2026-04-10 | `fc324d3547104276b827a68afc52ff2a11cc49c9` |
| actions/deploy-pages | v5.0.1 | 2026-09-01 | `368f82528645a54fb793d4d04e342629a3f51346` |

From `gh api repos/actions/<name>/releases/latest` and `gh api repos/actions/<name>/git/ref/tags/<tag>` (each returned
`object.type: commit`, so no annotated tag to dereference).

- Minimal workflow, from GitHub's starter (https://github.com/actions/starter-workflows/blob/main/pages/static.yml):
  `permissions: {contents: read, pages: write, id-token: write}`; `concurrency: {group: "pages", cancel-in-progress: false}`
  ("Allow only one concurrent deployment ... do NOT cancel in-progress runs"); the job has
  `environment: {name: github-pages, url: ${{ steps.deployment.outputs.page_url }}}`; steps checkout, configure-pages,
  upload-pages-artifact `with: path`, deploy-pages `id: deployment`. The starter still names older majors (@v5/@v3/@v5).
- deploy-pages needs at least `pages: write` and `id-token: write`, and should target `github-pages`
  (https://github.com/actions/deploy-pages/blob/v5.0.1/README.md; same in
  https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
- upload-pages-artifact `path`: "Path of the directory containing the static assets", default `_site/`; it tars the
  directory, excluding `.git`, `.github` and dotfiles unless `include-hidden-files: true`
  (https://github.com/actions/upload-pages-artifact/blob/v5.0.0/action.yml). The archive must be under 10 GB, with no
  symlinks or hard links (docs.github.com page above).
- Enable Pages: `POST /repos/{owner}/{repo}/pages` with body `build_type: workflow` (values `legacy`, `workflow`);
  201 created, 409 conflict; needs repo admin/maintainer or "manage GitHub Pages settings"
  (https://docs.github.com/en/rest/pages/pages#create-a-github-pages-site). E.g.
  `gh api -X POST repos/yellow-pine/noggin/pages -f build_type=workflow`. configure-pages' `enablement: true` could do it
  instead but needs a token other than `GITHUB_TOKEN` (https://github.com/actions/configure-pages/blob/v6.0.0/action.yml).

## Blender 5.2.2, Linux x64

- URL: https://download.blender.org/release/Blender5.2/blender-5.2.2-linux-x64.tar.xz (dated 15-Sep-2026,
  383295504 bytes, HTTP 200; https://download.blender.org/release/Blender5.2/).
- sha256 `84098912789dc450e95697c4184fb8a90acbe5111c2ba4aede3fecb57806a168`
  (https://download.blender.org/release/Blender5.2/blender-5.2.2.sha256).
- 5.2.3 also exists (22-Oct-2026, sha256 `78486c018b4443efe5e75ab54c290ed8c15abafd249b862c2c9ce2530a918eec`, same
  folder), 10 days old, so under the two-week rule; 5.2.2 stays the pin. No 5.3 folder yet (https://download.blender.org/release/).
