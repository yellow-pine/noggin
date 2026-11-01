# The repo holds sources only; CI builds every output and Pages serves one site

> Decided with Cansin on 2026-11-01, spec #224; ticket #225 (this ADR, the site and its deploy). Pictures (#226), docs
> numbers (#227), the skills bot (#228) and the reports (#229) follow it one ticket at a time.
> Amended 2026-11-01 (#280, spec #279): the site's home is a landing page (docs/index.md); the README is for
> contributors and stays on GitHub, off the site.
> Amended 2026-11-01 (#303, ADR 0010): release-please's release PR commits the generated CHANGELOG.md and the version
> bump, and switches on its own auto-merge; it lands through the required checks and review like any PR.
> Amended 2026-11-01 (#310): PRs run checks, main runs the same checks then deploys. Site Checks builds the site on
> both; Site Deploy deploys main's artifact once Code Checks and Site Checks passed, with no rebuild (only
> main's newest sim reports swapped in).
> Amended 2026-11-01 (#288): the jobs needing Chrome or Blender run in our own images in GHCR, built from ci/.
> Amended 2026-11-01 (#333, ADR 0012): Astro Starlight builds the site (`site/`), not MkDocs Material; the numbers'
> JSON from `macros.py` fills the same hidden markers; the built site's tests run in Site Checks, not `make check`.

Generated files in git drift from what made them: the README's pictures are copied into docs/images by hand, the sim
reports need a stamp check to catch a stale one, and the Markdown repeats numbers the code owns. So the repo holds
sources only: code, hand-written Markdown, configs, lockfiles (uv.lock, skills-lock.json) and measured data
(eyes/calibration.json, recorded sweeps). CI builds every output, keeps it in caches and artifacts, and deploys one
site to GitHub Pages from main. No bot commits: a bot may only open a PR.

- **One site, built from main.** Astro Starlight (the `site/` package, ADR 0012; MkDocs Material until #333) turns
  the repo's Markdown into the docs at the site's root, yellowpine.com/noggin/ (the org's custom domain); the web viewer
  (ADR 0008) sits at /viewer. The docs are the repo's Markdown as GitHub shows it, with no rewrite for the site, so
  a link to anything but a doc or a picture is an absolute GitHub URL (the site's tests fail on a link that lands
  nowhere, and the site carries no code).
- **Built once, deployed with GitHub's own Pages actions** (#310). Site Checks (`site-checks.yml`) builds the docs,
  the viewer's GLBs and the pictures on every PR and every push to main, and uploads the site as an artifact. Site
  Deploy (`pages.yml`) runs only on main: once both Code Checks and Site Checks passed for the commit, it downloads
  that run's artifact and deploys it with `actions/deploy-pages`; nothing built is committed, and no branch holds the site.
- **PR previews are artifacts.** A PR's `site` job builds the docs (and the viewer's GLBs when it changed what they are
  made from, #221) and uploads them as an artifact linked from its job summary; no external preview host. It is a required check (#245), and runs the built site's tests (ADR 0012).
- **Numbers come from the code.** A doc's numbers that the code owns (the behaviour table, each Stage guide's parts
  and servos, the picture sizes and colours in docs/model-notes.md, the wiring table and the viewer's Stage buttons,
  #306) are filled at build time: `macros.py` writes them as JSON and the site's Markdown plugin puts each in its
  doc's marker (ADR 0012). The markers sit in HTML comments, which GitHub hides, so GitHub shows the prose and a link to the site in
  their place; test_site.py fails if a number GitHub still shows in a doc (a duration, a Core's servo count) is not
  the code's (#227).
- **The sim reports are built, never committed** (#229). `make sim` writes them and their MJCFs into
  model/build/reports; check.yml's sim shard caches them under a key of what they are made from (`sim-`), so it
  runs the sim only when that changed. A PR that runs it diffs the new reports against main's latest
  (the newest `sim-` entry, which only main saves) in its job summary; Site Deploy runs once Code Checks and Site
  Checks are done on main (`workflow_run`) and puts the newest entry at /reports in the site it deploys (Site Checks
  builds beside Code Checks, before the sim may be saved). The stamp check (model/stale.py) is gone; the recorded sweeps
  (model/reports/*-report.json) and the exact-clearance fixture stay, as measured data.
- **The pictures are built in CI** (#226): Site Checks' `render` job renders the README's pictures in
  Blender before `site`, which serves them at /images, and the README points at those absolute URLs. A PR touching
  their inputs gets them as artifacts. Each motion renders on its own runner, a matrix read from the code (`make
  pictures-list`, #297), and `site` gathers them.
- **CI images are build outputs in the registry** (#288). The jobs that need a system tool uv can't install run in our
  own images, so they download no tool (a 403 from download.blender.org had taken the pictures down):
  ci/base.Dockerfile (Ubuntu with Python and uv, Node with mermaid-cli, Chrome for Testing, ngspice, each
  from a pinned source) for the site's build and viewer test (`site`; the diagram test's `code` once main has pushed a base with ngspice), and
  ci/blender.Dockerfile (base plus Blender, sha256-checked, and Mesa's software EGL) for `render` and `viewer`. The
  Dockerfiles are sources; the `CI Images` workflow builds the images into GHCR (`ghcr.io/yellow-pine/noggin-ci-base`,
  `-blender`), never committed, and those jobs pin them by digest (`container:`). Every other job stays on the bare
  runner with setup-uv and apt: pulling an image costs ~30-40 s a job, which a chain of them (convex, then a model
  shard) can't fit in the PR budget, and MuJoCo and CoACD are wheels. Python packages stay out of the images: `uv
  sync` in the job. Only main writes to the registry: it pushes `:main` with GitHub's build provenance when a
  Dockerfile changes and weekly without cache, and Dependabot proposes the new digests as a PR, whose checks run in
  them before any job on main does; a PR that changes a Dockerfile only builds the images, from main's cache read
  only.

## Considered options

- Committing the outputs (today's way, with stamps): rejected, it is what drifts.
- A `gh-pages` branch: rejected, it needs a bot commit per deploy.
- Netlify or Vercel previews per PR: rejected, a second host and account for what an artifact covers.
- Zensical, Material's successor from the same team (it reads `mkdocs.yml`): not yet, it is alpha; the move went
  to Astro Starlight instead (ADR 0012).
