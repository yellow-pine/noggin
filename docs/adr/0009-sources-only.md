# The repo holds sources only; CI builds every output and Pages serves one site

> Decided with Cansin on 2026-11-01, spec #224; ticket #225 (this ADR, the site and its deploy). Pictures (#226), docs
> numbers (#227), the skills bot (#228) and the reports (#229) follow it one ticket at a time.
> Amended 2026-11-01 (#280, spec #279): the site's home is a landing page (docs/index.md); the README is for
> contributors and stays on GitHub, off the site.
> Amended 2026-11-01 (#303, ADR 0010): release-please's release PR commits the generated CHANGELOG.md and the version
> bump, and switches on its own auto-merge; it lands through the required checks and review like any PR.
> Amended 2026-11-02 (#582, ADR 0017): no more: the version is the git tag and each release's notes are on its GitHub
> release, so nothing generated is committed.
> Amended 2026-11-01 (#310): PRs run checks, main runs the same checks then deploys. Site Checks builds the site on
> both; Site Deploy deploys main's artifact once Code Checks and Site Checks passed, with no rebuild (only
> main's newest sim reports swapped in).
> Amended 2026-11-01 (#288): the jobs needing Chrome or Blender run in our own images in GHCR, built from ci/.
> Amended 2026-11-01 (#333, ADR 0013): Astro Starlight builds the site (`site/`), not MkDocs Material; the numbers'
> JSON from `macros.py` fills the same hidden markers; the built site's tests run in Site Checks, not `make check`.
> Amended 2026-11-02 (#373, ADR 0014): each release's docs are built from its tag, attached to the release, and Site
> Deploy serves them at /noggin/vX.Y/ beside main's.
> Amended 2026-11-02 (#397): the README's CI/CD table is generated from .github/workflows into a cog block in the
> README, committed, and `cog --check` in `make check` fails while it is stale. The README is off the site (#280) yet
> GitHub must show the table, and GitHub renders committed Markdown only; a site page and a link would lose it there.
> Amended 2026-11-02 (#425): reverses #397. The committed table conflicted on every workflow PR and was too volatile
> for a README. Generated tables live on the site, never in a committed file (the README included): the CI/CD table
> is a site page (docs/ci-cd.md) filled from .github/workflows at build time like the other numbers, and the README
> links it.
> Amended 2026-11-02 (#472, spec #467): the CI images rebuild only when a Dockerfile changes, no weekly no-cache
> rebuild; the distro's security fixes arrive with Dependabot's base-image bumps (ADR 0012).
> Amended 2026-11-02 (#481, spec #467): the jobs run the CI images by the `:main` tag, not by digest; ci/pins goes.
> Amended 2026-11-02 (#529): gh in the base image from GitHub CLI's signed apt repo, unpinned (ADR 0012).
> Amended 2026-11-02 (#538, #496): Code Checks and Site Checks are one workflow, Checks (`checks.yml`), whose `Checks`
> gate fails unless every job before it passed or was skipped; Site Deploy deploys the site that gate uploads once
> main's Checks passed. Main's ruleset requires four checks: PR, Checks, Fetch Skills and Review.
> Amended 2026-11-02 (#534): reverses #472's "no weekly no-cache rebuild". `CI Images` also rebuilds both images
> weekly without the layer cache, Mondays before the image scan, so the archive's security fixes and the newest gh
> land without waiting for a base-image bump (ADR 0012).
> Amended 2026-11-02 (#547): commands now `just`, ADR 0016.
> Amended 2026-11-02 (#640, ADR 0019): CI builds no picture or GLB and the site serves none until the clean-room Mech.
> Amended 2026-11-02 (#649, ADR 0019): CI builds the Next Mech's pictures and GLB, and the site serves them.
> Amended 2026-11-02 (#696, Cansin): a PR's Checks run only Code (`just check-light`) and Site (the build and its HTML
> tests); the model, sim, Blender and Convex and the site's Chrome smoke build on main alone, which fixes forward.
> Amended 2026-11-02 (#714, Cansin): a PR's Checks run only Code (`just check-light`: ruff, pyright, the fast tests);
> the site's build and the workflow and Dockerfile linters moved to main too.
> Amended 2026-11-02 (#722, Cansin): that slim gate is its own workflow, PR Gate (`pr-gate.yml`: Code, then the
> required `Checks` gate), so a PR lists no job every PR skips; Checks (`checks.yml`) runs on main alone.
> Amended 2026-11-02 (#729, Cansin): no PR builds the CI images either; main's `CI Images` run fails without moving
> `:main`, and its failure files 'main red (CI Images)' (main-red.yml), which its next successful run closes.

Generated files in git drift from what made them: the README's pictures are copied into docs/images by hand, the sim
reports need a stamp check to catch a stale one, and the Markdown repeats numbers the code owns. So the repo holds
sources only: code, hand-written Markdown, configs, lockfiles (uv.lock, skills-lock.json) and measured data
(eyes/calibration.json, recorded sweeps). CI builds every output, keeps it in caches and artifacts, and deploys one
site to GitHub Pages from main. No bot commits: a bot may only open a PR.

- **One site, built from main.** Astro Starlight (the `site/` package, ADR 0013; MkDocs Material until #333) turns
  the repo's Markdown into the docs at the site's root, yellowpine.com/noggin/ (the org's custom domain); the web viewer
  (ADR 0008) sits at /viewer. The docs are the repo's Markdown as GitHub shows it, with no rewrite for the site, so
  a link to anything but a doc or a picture is an absolute GitHub URL (the site's tests fail on a link that lands
  nowhere, and the site carries no code).
- **Built once, deployed with GitHub's own Pages actions** (#310). Checks (`checks.yml`, #496) builds the docs
  on every PR and every push to main, with the viewer's GLBs and the pictures when their inputs changed, and its `Checks` gate uploads the site as an
  artifact. Site Deploy (`pages.yml`) runs only on main: once Checks passed for the commit, it downloads
  that run's artifact and deploys it with `actions/deploy-pages`; nothing built is committed, and no branch holds the site.
- **PR previews are artifacts.** A PR's Checks run builds the docs (and the viewer's GLBs when it changed what they
  are made from, #221) and its gate uploads them as an artifact linked from its job summary; no external preview host.
  The gate is the required `Checks` (#245, #496), and the run tests the built site (ADR 0013).
- **Numbers come from the code.** A doc's numbers that the code owns (the behaviour table, each Stage guide's parts
  and servos, the picture sizes and colours in docs/model-notes.md, the wiring table and the viewer's Stage buttons,
  #306, the CI/CD table from the workflows, #425) are filled at build time: `macros.py` writes them as JSON and the
  site's Markdown plugin puts each in its doc's marker (ADR 0013). The markers sit in HTML comments, which GitHub hides, so GitHub shows the prose and a link to the site in
  their place; test_site.py fails if a number GitHub still shows in a doc (a duration, a Core's servo count) is not
  the code's (#227).
- **The sim reports are built, never committed** (#229). `just sim` writes them and their MJCFs into
  model/build/reports; a `Model` shard caches them under a key of what they are made from (`sim-`), so it
  runs the sim only when that changed. A PR that runs it diffs the new reports against main's latest
  (the newest `sim-` entry, which only main saves) in its job summary; Site Deploy runs once Checks is done on main
  (`workflow_run`) and puts the newest entry at /reports in the site it deploys (Checks' `Site` builds beside the
  `Model` shards, before the sim may be saved). The stamp check (model/stale.py) is gone; the recorded sweeps
  (model/reports/*-report.json) and the exact-clearance fixture stay, as measured data.
- **The pictures are built in CI** (#226): Checks' `Blender` jobs render the README's pictures, and `Site`, after
  them, adds them to the site (#732), which serves them at /images, and the README points at those absolute URLs. A
  PR touching their inputs gets them as artifacts. The motions and the viewer are packed into Blender runners longest
  first, a matrix read from the code (`just blender-bins`, #297, #496), and the gate gathers them.
- **CI images are build outputs in the registry** (#288). The jobs that need a system tool uv can't install run in our
  own images, so they download no tool (a 403 from download.blender.org had taken the pictures down):
  ci/base.Dockerfile (Ubuntu with Python and uv, Node with mermaid-cli, Chrome for Testing, ngspice, each
  from a pinned source but gh, from GitHub CLI's signed apt repo at its newest, ADR 0012) for the site's build
  (`Site`) and the tests not marked model (`Code`), and
  ci/blender.Dockerfile (base plus Blender, sha256-checked, and Mesa's software EGL) for the pictures and the viewer
  (`Blender`). The
  Dockerfiles are sources; the `CI Images` workflow builds the images into GHCR (`ghcr.io/yellow-pine/noggin-ci-base`,
  `-blender`), never committed, and those jobs run them by the `:main` tag (`container:`, #481): mutable, but only
  main's `CI Images` run writes it, and Dependabot keeps the Dockerfiles' own base images digest-pinned and current.
  Every other job stays on the bare runner with setup-uv and apt: pulling an image costs ~30-40 s a job, which a chain
  of them (convex, then a model shard) can't fit in the PR budget, and MuJoCo and CoACD are wheels. The base image
  carries uv's Python and the venv synced from uv.lock, which its jobs link as `.venv`, so `uv sync` in the job only
  installs what a newer uv.lock changed (#725). Only main writes to the registry: it pushes `:main` with GitHub's build
  provenance when a Dockerfile or the venv's inputs (uv.lock, pyproject.toml, .python-version) change (Dependabot's
  bumps among them, #472) and weekly without the layer cache (#534), and every job that starts after runs in them. No
  PR builds them (#729): a broken Dockerfile fails main's run, which leaves `:main` as it was and files 'main red'.

## Known limits

Accepted as-is: the jobs' `:main` is mutable. Only main's `CI Images` run writes it (its push job, which runs on main
alone, is the only one granted GHCR's `packages: write`); Cansin chose it over a custom digest-pin bump on 2026-11-02
(#481). Both packages are public, owned by the yellow-pine org and linked to yellow-pine/noggin, whose only
collaborator (and the org's only member) is Cansin, admin (`gh api`, 2026-11-02); whether they inherit the repo's
access and grant no other repo Actions access is a package setting the API does not show, unchecked. A main push
that changes a Dockerfile may run Checks' `Blender` jobs in the previous `:main` and cache those pictures under the new
Dockerfile hash until another input changes.

## Considered options

- Committing the outputs (today's way, with stamps): rejected, it is what drifts.
- A `gh-pages` branch: rejected, it needs a bot commit per deploy.
- Netlify or Vercel previews per PR: rejected, a second host and account for what an artifact covers.
- Zensical, Material's successor from the same team (it reads `mkdocs.yml`): not yet, it is alpha; the move went
  to Astro Starlight instead (ADR 0013).
- The jobs' images pinned by digest in ci/pins/Dockerfile, which Dependabot bumped and an `Images` job per workflow
  read (#444): rejected 2026-11-02 (#481), custom glue for what the `:main` tag gives.
