# Each Release's docs are built from its tag, kept as a release asset, and served beside main's

> Decided with Cansin on 2026-11-01, #307 item 3; ticket #373. Research: #331's comments ("2. Versioned docs").

A reader with a Mech built at noggin v0.2 needs v0.2's docs, not main's. Neither Astro nor Starlight versions docs,
and starlight-versions archives each version's pages into the repo, which ADR 0009 forbids. So each Release builds
its own docs once and keeps them as a release asset, and every deploy serves them beside main's.

- **Latest at /noggin/, each Release's docs at /noggin/vX.Y/.** The site's base comes from `SITE_BASE` (default
  `/noggin`, `site/src/pages.mjs`), so links between docs and every Starlight asset stay inside the version. Only the
  newest patch of a minor is served: vX.Y.Z's docs are vX.Y's.
- **Built once, at the tag** (Release Assets, `release.yml`): `SITE_BASE=/noggin/vX.Y make site`, the viewer's GLBs
  fetched from the live site (the release commit's model: its PR only bumps the version), packed as
  `noggin-docs-vX.Y.Z.tar.gz` and attached to the release, whose notes then link /noggin/vX.Y/. A prerelease builds
  none: it is never served. Each version carries its own Pagefind index.
- **Assembled at deploy** (Site Deploy, `pages.yml`): `scripts/docs_versions.py` unpacks every release's docs asset
  (no drafts, no prereleases) into the site Site Checks built, at vX.Y/, and writes `versions.json` in Material for
  MkDocs' format (`version`, `title`, `aliases`), latest first. A deploy without releases ships the build's own
  `versions.json`, latest alone. No branch holds the site and nothing built is committed (ADR 0009). Main's docs are
  `latest` (#373), not mike's `dev` (#307): here latest is what the reader gets at /noggin/, not an alias of the
  newest release.
- **The switcher is ours**: a `<select>` in the header (`site/src/components/VersionSelect.astro`, beside Starlight's
  social links) that reads /noggin/versions.json at view time, so an old version lists the newer ones, and goes to the
  same page in the chosen version, or to its home when that page isn't there.
- **The pictures and the sim reports are the live site's** in every version: the Markdown links the pictures by
  absolute URL, and the sidebar's Reports link goes to /noggin/reports/ outside latest.
- **Tested at the seam**: Site Checks builds the site again under `/noggin/v0.0` and runs the link tests on it (every
  link lands inside the version, or on the live site's pictures, viewer and reports); scripts/test_docs_versions.py
  checks which releases are served; the smoke test checks the switcher on latest.

## Considered options

- starlight-versions: snapshots pages into `src/content/docs/<version>/` in the repo (against ADR 0009) and assumes
  `src/content/docs`.
- mike (a `gh-pages` branch per version): a bot commit per deploy, and MkDocs only.
- Rebuilding every release's docs at each deploy: slower, and an old tag's build can break with today's tools; the
  asset is built once and never changes.
- One path per patch (/noggin/vX.Y.Z/): a patch fixes, so its docs replace its minor's.
