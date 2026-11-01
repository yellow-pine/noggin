# The site is Astro Starlight over the repo's Markdown, with a hash-based CSP

> Decided with Cansin on 2026-11-01, spec #331 (research and the CSP spike's verdict in its comments, spike #332);
> ticket #333. Supersedes ADR 0009's MkDocs Material and mkdocs-macros, and ADR 0008's page, import map and vendored
> three.js.

Material for MkDocs reaches end of life on 2027-05-05, and MkDocs 1.x is frozen while 2.0 drops plugins. The site
moves to [Astro Starlight](https://starlight.astro.build) with its default look: a maintained, widely used tool that
keeps the site's must-haves (numbers from the code, the viewer inside the theme, a self-only CSP), with no paid
service anywhere.

- **One npm package in `site/`.** package.json, its lockfile, astro.config.mjs, the content loader, the Markdown
  plugins, the viewer's page and module, and their tests. Node 24 LTS (`site/.nvmrc`, `engines`), npm, no monorepo
  tool until a second JS package exists. `make site` still builds everything: `python -m macros`, `npm ci`, `astro
  build` into `site/dist`, then the GLBs, pictures and reports beside it. Install scripts are denied
  (`allowScripts`): mermaid-cli's Puppeteer drives the installed Chrome, as Playwright does.
- **The Markdown stays where it is, with no front matter.** Astro's `glob()` loader reads the repo's Markdown in place
  (`site/src/pages.mjs`: the root's `*.md` and `docs/**`, not the README, CLAUDE.md or docs/references) into
  Starlight's docs collection with `docsSchema()`. A page's id is its path, lower-cased; docs/index.md is the home
  page, a splash. Starlight needs a `title`: the loader takes it from the page's H1, and a Markdown plugin drops the
  H1 itself, so Starlight draws it once. Pages read the same on GitHub and on the site.
- **Markdown plugins on Astro's default processor, Sätteri** (`site/src/markdown.mjs`): a relative `.md` link goes to
  its page (or to GitHub when the doc is not a page); `<!--{{ name }}-->` takes the Markdown `macros.py` writes as
  JSON (`site/src/macros.json`, never committed), an unknown name fails the build, and a `<!--{# ... #}-->` span
  (what GitHub shows in a table's place) goes. GitHub-style alerts (`> [!WARNING]`) become Starlight asides
  (starlight-github-alerts); buttons are plain links.
- **Starlight's own features first**: Pagefind for search, `sidebar` for the nav (every ADR listed from the files),
  `editLink`, `social` with a small header component that asks api.github.com for the stars and forks in the browser,
  `<StarlightPage>` for the viewer's page. Mermaid renders in the browser with astro-mermaid from npm.
- **The viewer is an Astro page** (`site/src/pages/viewer.astro`, ADR 0008): its module imports three.js and its
  addons from npm and Vite bundles them; the Draco decoder is copied from three's package into the build. The
  lockfile's integrity hashes and Dependabot replace vendored.py's sha384 pins.
- **A hash-based CSP, one policy for every page** (Astro's `security.csp`, in a `<meta>`). Scripts: `'self'` plus a
  hash for each inline script, never `'unsafe-inline'`. Astro hashes the scripts it bundles; Starlight's `is:inline`
  scripts (theme, menu, sidebar) it does not, so `site/src/csp.mjs` adds each built page's missing hashes once the
  site is built: derived, never listed by hand (ADR 0011), and a Starlight upgrade needs no edit. Styles: `'self'`
  and **`'unsafe-inline'`** for `style=""` attributes and `<style>` elements, because Expressive Code (Shiki) writes
  style attributes and Mermaid injects `<style>` at run time, which no hash can cover. The viewer's Draco decoder
  needs `'wasm-unsafe-eval'` and `worker-src blob:`, GLTFLoader's textures `connect-src blob:`, the header
  `connect-src https://api.github.com`, Starlight's icons `img-src data:`, the pictures' absolute URLs
  `img-src https://yellowpine.com/noggin/images/` (the site itself, and in a local preview too). Pagefind 1.6 needs
  nothing more: its worker is the site's own.
- **Fresh URLs, no redirects.** Starlight's paths under /noggin/: docs/ keeps its paths (/noggin/docs/build/parts/),
  the root's pages are lower-cased (/noggin/glossary/).
- **Tests at the built site's seam.** Vitest over `site/dist` (`site/site.test.mjs`): every doc a page titled by its
  H1, every link lands, each number the JSON's, every inline script hashed in the CSP, no photo; and every diagram
  drawn by mermaid-cli (a devDependency, so the lockfile pins the Mermaid it uses, the site's). One Playwright smoke
  test in the installed Chrome (`site/smoke.pw.mjs`): the viewer plays a gesture and switches Stage, search finds a
  page, the diagrams draw, with no CSP violation and no request to another host but api.github.com. pytest keeps the
  Python-only checks (the numbers macros.py derives, the README, photos out of git, the workflows).
- **CI keeps its shape** (#310): Site Checks' `site` job sets up Node by `.nvmrc` with npm's cache, runs `make site`,
  then Vitest and Playwright, and uploads `site/dist`; Site Deploy deploys it. Dependabot covers npm, grouped like
  uv and Actions, each release waiting 14 days.

## Considered options

- Zensical (Material's successor, reads mkdocs.yml): rejected for now, 0.x with no hooks or plugin API yet, and
  `docs_dir: .` unsupported (#331's research).
- ProperDocs + Material: buys time only until Material's end of life.
- Docusaurus: built-in versions snapshot pages into the repo (against ADR 0009); VitePress: 2.0 still alpha, no
  Mermaid or versions.
- Starlight's `docsLoader()`: reads `src/content/docs/` only, so the Markdown would move out of its place.
- MDX components (`<CardGrid>`, `<Aside>`) for cards and callouts: GitHub would show their imports and JSX.
- Hand-listing Starlight's inline-script hashes in the config: they change with each Starlight release.
- `'unsafe-inline'` for scripts (the MkDocs policy): not needed, every script is the site's own or hashed.
- rehype-mermaid (build-time SVGs, no style injection): no release since 2024 and it pins Mermaid 11.
