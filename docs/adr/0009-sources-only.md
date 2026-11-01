# The repo holds sources only; CI builds every output and Pages serves one site

> Decided with Cansin on 2026-11-01, spec #224; ticket #225 (this ADR, the site and its deploy). Pictures (#226), docs
> numbers (#227), the skills bot (#228) and the reports (#229) follow it one ticket at a time.

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
- **Deployed with GitHub's own Pages actions.** The `pages` workflow builds the docs and the viewer's GLBs on a push to
  main and deploys them together with `actions/deploy-pages`; nothing built is committed, and no branch holds the site.
- **PR previews are artifacts.** A PR's `site` job builds the docs and uploads them as an artifact linked from its
  job summary; no external preview host. It is not a required check: `make check` builds the docs strictly too
  (test_site.py), so a broken page or link fails the required one.
- **Until their tickets land**, the pictures in docs/images and the reports in model/reports stay in git as they are.

## Considered options

- Committing the outputs (today's way, with stamps): rejected, it is what drifts.
- A `gh-pages` branch: rejected, it needs a bot commit per deploy.
- Netlify or Vercel previews per PR: rejected, a second host and account for what an artifact covers.
- Zensical, Material's successor from the same team (it reads `mkdocs.yml`): not yet, it is alpha; Material is
  maintained through May 2027, so the move is a later ticket.
