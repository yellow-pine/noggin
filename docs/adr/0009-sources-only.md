# The repo holds sources only; CI builds every output and Pages serves one site

> Decided with Cansin on 2026-11-01, spec #224; ticket #225 (this ADR, the site and its deploy). Pictures (#226), docs
> numbers (#227), the skills bot (#228) and the reports (#229) follow it one ticket at a time.
> Amended 2026-11-01 (#280, spec #279): the site's home is a landing page (docs/index.md); the README is for
> contributors and stays on GitHub, off the site.

Generated files in git drift from what made them: the README's pictures are copied into docs/images by hand, the sim
reports need a stamp check to catch a stale one, and the Markdown repeats numbers the code owns. So the repo holds
sources only: code, hand-written Markdown, configs, lockfiles (uv.lock, skills-lock.json) and measured data
(eyes/calibration.json, recorded sweeps). CI builds every output, keeps it in caches and artifacts, and deploys one
site to GitHub Pages from main. No bot commits: a bot may only open a PR.

- **One site, built from main.** MkDocs Material (pinned in the dev group, `mkdocs.yml` at the root) turns the repo's
  Markdown into the docs at the site's root, yellowpine.com/noggin/ (the org's custom domain); the web viewer
  (ADR 0008) sits at /viewer. The docs are the repo's Markdown as GitHub shows it, with no rewrite for the site, so
  a link to anything but a doc or a picture is an absolute GitHub URL (the build is strict and the site carries no
  code).
- **Deployed with GitHub's own Pages actions.** The `pages` workflow builds the docs and the viewer's GLBs once the
  check workflow is done with a push to main and deploys them together with `actions/deploy-pages`; nothing built is committed, and no branch holds the site.
- **PR previews are artifacts.** A PR's `site` job builds the docs (and the viewer's GLBs when it changed what they are
  made from, #221) and uploads them as an artifact linked from its job summary; no external preview host. It is a required check (#245), beside `make check`, which builds the docs
  strictly too (test_site.py).
- **Numbers come from the code.** A doc's numbers that the code owns (the behaviour table, each Stage guide's parts and servos, the picture sizes
  and colours in docs/model-notes.md) are filled at build time by mkdocs-macros (`macros.py`, pinned in the dev group),
  on the pages `mkdocs.yml` lists only. Its Jinja sits in HTML comments, which GitHub hides, so GitHub shows the prose
  and a link to the site in their place; test_site.py fails if a number GitHub still shows in a doc (a duration, a
  Core's servo count) is not the code's (#227).
- **The sim reports are built, never committed** (#229). `make sim` writes them and their MJCFs into
  model/build/reports; check.yml's sim shard caches them under a key of what they are made from (`sim-`), so it
  runs the sim only when that changed. A PR that runs it diffs the new reports against main's latest
  (the newest `sim-` entry, which only main saves) in its job summary; the pages workflow runs once check is done on
  main (`workflow_run`) and publishes the newest entry at /reports. The stamp check (model/stale.py) is gone; the
  recorded sweeps (model/reports/*-report.json) and the exact-clearance fixture stay, as measured data.
- **The pictures are built in CI** (#226): the pages workflow's `render` job renders the README's pictures in
  Blender before `site`, which serves them at /images, and the README points at those absolute URLs. A PR touching
  their inputs gets them as artifacts.

## Considered options

- Committing the outputs (today's way, with stamps): rejected, it is what drifts.
- A `gh-pages` branch: rejected, it needs a bot commit per deploy.
- Netlify or Vercel previews per PR: rejected, a second host and account for what an artifact covers.
- Zensical, Material's successor from the same team (it reads `mkdocs.yml`): not yet, it is alpha; Material is
  maintained through May 2027, so the move is a later ticket.
