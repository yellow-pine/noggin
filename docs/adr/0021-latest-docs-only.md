# The site serves the latest docs alone, labelled with the newest release

> Decided by Cansin on 2026-11-02, #778; how the label and the redirect work was decided while he was away (#778's
> "Decision (made while away)" comment). Supersedes ADR 0014.

Each Release's docs, kept as a release asset and served at /noggin/vX.Y/ beside main's (ADR 0014), broke as the site
moved on: they linked outputs later changes took down (#645's), and keeping every old build working was not worth it.
So the site serves one set of docs, main's, at /noggin/.

- **Labelled with the newest release.** Where the version switcher was, the header names GitHub's newest release, "vX.Y.Z
  (latest)", linking its notes. The reader's browser asks api.github.com for it at view time, as it does for the stars
  and forks, so the label is right the moment a release is tagged: the site is built before its commit's tag exists.
  When GitHub doesn't answer (a rate limit), there is no label; the footer still names the version built.
- **Old URLs land on the docs.** /noggin/vX.Y/… and /noggin/vX.Y.Z/… reach GitHub Pages' 404 page, whose script sends
  the reader on to the same page under /noggin/, or to the home when that page is gone too.
- **Nothing versioned is built or kept.** Release Assets attaches the Core program zip alone, Site Deploy deploys
  Checks' artifact with main's sim reports and nothing else, and nothing dispatches it. The docs assets already on old
  releases stay there, unserved.

## Considered options

- The label from the build (git describe's last tag): no request, but one release behind on the commit that releases,
  until the next merge rebuilds the site.
- The label written at deploy: needs Release to dispatch a deploy after tagging again, the coupling this drops.
- A redirect page per old version: a deploy-time list of versions for a few stale links; one 404 script covers them all.
